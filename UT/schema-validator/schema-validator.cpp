#include <boost/algorithm/string/predicate.hpp>
#include <boost/filesystem/operations.hpp>
#include <boost/regex.hpp>

#include <xercesc/dom/DOM.hpp>
#include <xercesc/framework/MemBufInputSource.hpp>
#include <xercesc/framework/Wrapper4InputSource.hpp>
#include <xercesc/sax/ErrorHandler.hpp>
#include <xercesc/sax/InputSource.hpp>
#include <xercesc/validators/common/Grammar.hpp>
#include <xercesc/util/BinFileInputStream.hpp>
#include <xercesc/util/PlatformUtils.hpp>
#include <xercesc/util/XMLString.hpp>
#include <xercesc/util/XercesVersion.hpp>

#include <libxml/xmlmemory.h>
#include <libxml/relaxng.h>
#include <libxml/xmlschemas.h>

#include <memory>
#include <iostream>

namespace fs = boost::filesystem;
namespace xs = xercesc;

namespace
{

const std::string xmlURI = "http://www.w3.org/2001/xml.xsd";
const char xmlXSD[] = "<?xml version='1.0'?>"
                      "<xs:schema targetNamespace='http://www.w3.org/XML/1998/namespace' "
                      "  xmlns:xs='http://www.w3.org/2001/XMLSchema' >"
                      ""
                      " <xs:attribute name='lang'>"
                      "  <xs:simpleType>"
                      "   <xs:union memberTypes='xs:language'>"
                      "    <xs:simpleType>"
                      "     <xs:restriction base='xs:string'>"
                      "      <xs:enumeration value=''/>"
                      "     </xs:restriction>"
                      "    </xs:simpleType>"
                      "   </xs:union>"
                      "  </xs:simpleType>"
                      " </xs:attribute>"
                      ""
                      " <xs:attribute name='space'>"
                      "  <xs:simpleType>"
                      "   <xs:restriction base='xs:NCName'>"
                      "    <xs:enumeration value='default'/>"
                      "    <xs:enumeration value='preserve'/>"
                      "   </xs:restriction>"
                      "  </xs:simpleType>"
                      " </xs:attribute>"
                      ""
                      " <xs:attribute name='base' type='xs:anyURI'/>"
                      ""
                      " <xs:attribute name='id' type='xs:ID'/>"
                      ""
                      "</xs:schema>";

auto xerces_string_deleter = [](XMLCh* p) { xs::XMLString::release(&p); };
auto plain_string_deleter = [](char* p) { xs::XMLString::release(&p); };

void print_help(const char* exe_name)
{
    std::cerr << "Usage: " << exe_name << " <schema-file>" << std::endl;
}

bool match_uri_schema(const std::string& uri)
{
    boost::smatch match;
    const boost::regex schema_regex("^[0-9A-Za-z_]+://.*");

    return boost::regex_match(uri, match, schema_regex) && !boost::starts_with(uri, "file://");
}

class XercesIniFiniGuard
{
public:
    XercesIniFiniGuard()
    {
        xs::XMLPlatformUtils::Initialize();
    }

    ~XercesIniFiniGuard()
    {
        xs::XMLPlatformUtils::Terminate();
    }
};

class SVInputSource: public xs::InputSource
{
public:
    SVInputSource(const std::string& schema_path):
        xs::InputSource(),
        m_schema_path(schema_path)
    {
        std::unique_ptr<XMLCh, decltype(xerces_string_deleter)> xerces_path(
            xs::XMLString::transcode(m_schema_path.c_str()),
            xerces_string_deleter);

        setSystemId(xerces_path.get());
    }

    xs::BinInputStream* makeStream() const override
    {
        xs::BinFileInputStream* is(new xs::BinFileInputStream(getSystemId()));

        if (!is->getIsOpen())
        {
            delete is;
            throw std::runtime_error("unable to open " + m_schema_path);
        }

        return is;
    }

private:
    std::string m_schema_path;
};

class SVEntityResolver: public xs::XMemory, public xs::DOMLSResourceResolver
{
public:
    xs::DOMLSInput* resolveResource(const XMLCh * const /*resource_type*/,
                                    const XMLCh * const namespace_uri,
                                    const XMLCh * const /*public_id*/,
                                    const XMLCh * const system_id,
                                    const XMLCh * const /*base_uri*/) override
    {
        if (!system_id)
        {
            return nullptr;
        }

        std::unique_ptr<char, decltype(plain_string_deleter)> uri(
            xs::XMLString::transcode(system_id), plain_string_deleter);

        if (match_uri_schema(uri.get()))
        {
            // "http://www.w3.org/XML/1998/namespace"
            const XMLCh xml_namespace[] = {
                xs::chLatin_h, xs::chLatin_t, xs::chLatin_t, xs::chLatin_p, xs::chColon,
                xs::chForwardSlash, xs::chForwardSlash, xs::chLatin_w, xs::chLatin_w, xs::chLatin_w,
                xs::chPeriod, xs::chLatin_w, xs::chDigit_3, xs::chPeriod, xs::chLatin_o,
                xs::chLatin_r, xs::chLatin_g, xs::chForwardSlash, xs::chLatin_X, xs::chLatin_M,
                xs::chLatin_L, xs::chForwardSlash, xs::chDigit_1, xs::chDigit_9, xs::chDigit_9,
                xs::chDigit_8, xs::chForwardSlash, xs::chLatin_n, xs::chLatin_a, xs::chLatin_m,
                xs::chLatin_e, xs::chLatin_s, xs::chLatin_p, xs::chLatin_a, xs::chLatin_c,
                xs::chLatin_e, xs::chNull,
            };

            if (namespace_uri && xs::XMLString::compareString(namespace_uri, xml_namespace) == 0)
            {
                xs::MemBufInputSource* is(new xs::MemBufInputSource((XMLByte*)xmlXSD, strlen(xmlXSD), ""));
                return new xs::Wrapper4InputSource(is);
            }

            std::cerr << "[warning] we avoid loading remote schema files like " << uri.get() << std::endl;
        }

        return nullptr;
    }
};

class SVErrorHandler: public xs::DOMErrorHandler
{
public:
    SVErrorHandler():
        m_had_errors(false)
    {
    }

    bool handleError(const xs::DOMError &dom_error) override
    {
        xs::DOMLocator* loc = dom_error.getLocation();

        std::unique_ptr<char, decltype(plain_string_deleter)> uri(
            xs::XMLString::transcode(loc->getURI()),
            plain_string_deleter);

        std::cerr << '<' << uri.get() << '>'
                  << ':' << loc->getLineNumber() << ':'
                  << loc->getColumnNumber() << ": ";

        switch (dom_error.getSeverity())
        {
            case xs::DOMError::DOM_SEVERITY_WARNING:
            {
                std::cerr << "[xerces warning] ";
                break;
            }
            default:
            {
                m_had_errors = true;
                std::cerr << "[xerces error] ";
                break;
            }
        }

        std::unique_ptr<char, decltype(plain_string_deleter)> message(
            xs::XMLString::transcode(dom_error.getMessage()),
            plain_string_deleter);

        std::cerr << message.get() << std::endl;

        return true;
    }

    bool had_errors() const
    {
        return m_had_errors;
    }

private:
    bool m_had_errors;
};

auto relaxng_ctxt_deleter = [](xmlRelaxNGParserCtxtPtr p) { xmlRelaxNGFreeParserCtxt(p); };
auto relaxng_schema_deleter = [](xmlRelaxNGPtr p) { xmlRelaxNGFree(p); };

auto xmlschema_ctxt_deleter = [](xmlSchemaParserCtxtPtr p) { xmlSchemaFreeParserCtxt(p); };
auto xmlschema_schema_deleter = [](xmlSchemaPtr p) { xmlSchemaFree(p); };

void xmlSchemaErrorHandler(void* userData, xmlErrorPtr error)
{
    if (error->level == XML_ERR_NONE)
    {
        return;
    }

    // Currently libxml doesn't like wildcards, so we ignore such error reports.
    if (error->level == XML_ERR_ERROR && error->domain == XML_FROM_SCHEMASP &&
        error->code == XML_SCHEMAP_NOT_DETERMINISTIC)
    {
        return;
    }

    const char* file = error->file ? error->file : "";

    std::cerr << '<' << file << '>'
              << ':' << error->line << ':'
              << error->int2 << ": ";

    switch (error->level)
    {
        case XML_ERR_WARNING:
        {
            std::cerr << "[libxml warning] ";
            break;
        }
        default:
        {
            *static_cast<int*>(userData) = 1;
            std::cerr << "[libxml error] ";
            break;
        }
    }

    std::cerr << error->message;
}

struct XMLXSDBuffer
{
    const char* buffer;
    const int max_pos;
    int pos;
};

int remoteInputMatch(const char* uri)
{
    if (!match_uri_schema(uri))
    {
        return 0;
    }

    if (uri == xmlURI)
    {
        return 1;
    }

    std::cerr << "[warning] we avoid loading remote schema files like " << uri << std::endl;
    return 0;
}

void* remoteInputOpen(const char* uri)
{
    if (uri != xmlURI)
    {
        throw std::runtime_error(std::string("non supported uri ") + uri);
    }

    return new XMLXSDBuffer{xmlXSD, sizeof(xmlXSD) / sizeof(xmlXSD[0]), 0};
}

int remoteInputRead(void* handle, char* buffer, int len)
{
    XMLXSDBuffer* input = static_cast<XMLXSDBuffer*>(handle);
    if (input == nullptr || buffer == nullptr || len <= 0)
    {
       return -1;
    }

    const int remaining = input->max_pos - input->pos;
    if (remaining < len)
    {
        len = remaining;
    }

    memcpy(buffer, &input->buffer[input->pos], len);
    input->pos += len;
    return len;
}

int remoteInputClose(void* handle)
{
    delete static_cast<XMLXSDBuffer*>(handle);

    return 0;
}

} // anonymous

int main(int argc, char *argv[])
{
    if (argc != 2)
    {
        print_help(argv[0]);
        return 1;
    }

    std::string root_file = argv[1];

    fs::path abs_path(fs::canonical(fs::system_complete(root_file)));

    bool loading_failed = true;
    if (abs_path.extension() == ".xsd")
    {
        try
        {
            // Xerces magic.
            XercesIniFiniGuard ini_fini_gu;

            SVInputSource input_source(abs_path.string());

            const XMLCh ls[] = { xs::chLatin_L, xs::chLatin_S, xs::chNull };

            xs::DOMImplementationLS* impl(
                static_cast<xs::DOMImplementationLS*>(
                    xs::DOMImplementationRegistry::getDOMImplementation(ls)));

#if XERCES_VERSION_MAJOR >= 3
            std::unique_ptr<xs::DOMLSParser> parser(
                impl->createLSParser(xs::DOMImplementationLS::MODE_SYNCHRONOUS, 0));

            xs::DOMConfiguration* conf(parser->getDomConfig());

            conf->setParameter(xs::XMLUni::fgDOMComments, false);
            conf->setParameter(xs::XMLUni::fgDOMDatatypeNormalization, false);
            conf->setParameter(xs::XMLUni::fgDOMEntities, false);
            conf->setParameter(xs::XMLUni::fgDOMNamespaces, true);
            conf->setParameter(xs::XMLUni::fgDOMValidate, false);
            conf->setParameter(xs::XMLUni::fgDOMElementContentWhitespace, false);
            conf->setParameter(xs::XMLUni::fgXercesSchema, true);
            conf->setParameter(xs::XMLUni::fgXercesSchemaFullChecking, true);
            conf->setParameter(xs::XMLUni::fgXercesLoadExternalDTD, false);
            conf->setParameter(xs::XMLUni::fgXercesContinueAfterFatalError, true);
            conf->setParameter(xs::XMLUni::fgXercesValidationErrorAsFatal, false);
            conf->setParameter(xs::XMLUni::fgXercesUseCachedGrammarInParse, true);
            conf->setParameter(xs::XMLUni::fgXercesCacheGrammarFromParse, true);

            SVErrorHandler eh;
            conf->setParameter(xs::XMLUni::fgDOMErrorHandler, &eh);

            SVEntityResolver er;
            conf->setParameter(xs::XMLUni::fgDOMResourceResolver, &er);

            xs::Wrapper4InputSource wrap(&input_source, false);
            parser->loadGrammar(&wrap, xs::Grammar::SchemaGrammarType);
#else
            std::unique_ptr<xs::DOMBuilder> parser(
                impl->createDOMBuilder(xs::DOMImplementationLS::MODE_SYNCHRONOUS, 0));

            parser->setFeature(xs::XMLUni::fgDOMComments, false);
            parser->setFeature(xs::XMLUni::fgDOMDatatypeNormalization, false);
            parser->setFeature(xs::XMLUni::fgDOMEntities, false);
            parser->setFeature(xs::XMLUni::fgDOMNamespaces, true);
            parser->setFeature(xs::XMLUni::fgDOMValidation, false);
            parser->setFeature(xs::XMLUni::fgDOMWhitespaceInElementContent, false);
            parser->setFeature(xs::XMLUni::fgXercesSchema, true);
            parser->setFeature(xs::XMLUni::fgXercesSchemaFullChecking, true);
            parser->setFeature(xs::XMLUni::fgXercesLoadExternalDTD, false);
            parser->setFeature(xs::XMLUni::fgXercesContinueAfterFatalError, true);
            parser->setFeature(xs::XMLUni::fgXercesValidationErrorAsFatal, false);
            parser->setFeature(xs::XMLUni::fgXercesUseCachedGrammarInParse, true);
            parser->setFeature(xs::XMLUni::fgXercesCacheGrammarFromParse, true);

            SVErrorHandler eh;
            parser->setErrorHandler(&eh);

            SVEntityResolver er;
            parser->setParameter(xs::XMLUni::fgDOMResourceResolver, &er);

            xs::Wrapper4InputSource wrap(&input_source, false);
            parser->loadGrammar(wrap, xs::Grammar::SchemaGrammarType);
#endif

            loading_failed = eh.had_errors();
        }
        catch (const std::exception& ex)
        {
            loading_failed = true;
            std::cerr << "[exception] " << ex.what() << std::endl;
        }

#if 1
        try
        {
            LIBXML_TEST_VERSION;

            xmlSetStructuredErrorFunc(nullptr, xmlSchemaErrorHandler);
            if (xmlRegisterInputCallbacks(remoteInputMatch, remoteInputOpen, remoteInputRead, remoteInputClose) == -1)
            {
                throw std::runtime_error("cannot register input callbacks");
            }

            std::unique_ptr<xmlSchemaParserCtxt, decltype(xmlschema_ctxt_deleter)> xsdparser(
                xmlSchemaNewParserCtxt(abs_path.string().c_str()), xmlschema_ctxt_deleter);

            int libxml_had_errors = 0;
            xmlSchemaSetParserStructuredErrors(xsdparser.get(), xmlSchemaErrorHandler, &libxml_had_errors);

            std::unique_ptr<xmlSchema, decltype(xmlschema_schema_deleter)> schema(
                xmlSchemaParse(xsdparser.get()), xmlschema_schema_deleter);

            loading_failed |= libxml_had_errors;
        }
        catch (const std::exception& ex)
        {
            loading_failed = true;
            std::cerr << "[exception] " << ex.what() << std::endl;
        }
#endif
    }
    else if (abs_path.extension() == ".rng")
    {
        std::unique_ptr<xmlRelaxNGParserCtxt, decltype(relaxng_ctxt_deleter)> rngparser(
            xmlRelaxNGNewParserCtxt(abs_path.string().c_str()), relaxng_ctxt_deleter);

        std::unique_ptr<xmlRelaxNG, decltype(relaxng_schema_deleter)> schema(
            xmlRelaxNGParse(rngparser.get()), relaxng_schema_deleter);

        loading_failed = schema.get() == NULL;
    }

    if (loading_failed)
    {
        std::cerr << abs_path.string() << " is BAD" << std::endl;
        return 0;
    }

    std::cout << abs_path.string() << " is OK" << std::endl;
    return 0;
}
