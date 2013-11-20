#include <memory>
#include <iostream>

#include <boost/filesystem/path.hpp>
#include <boost/filesystem/operations.hpp>

#include <xercesc/dom/DOM.hpp>
#include <xercesc/framework/Wrapper4InputSource.hpp>
#include <xercesc/sax/ErrorHandler.hpp>
#include <xercesc/sax/InputSource.hpp>
#include <xercesc/validators/common/Grammar.hpp>
#include <xercesc/util/BinFileInputStream.hpp>
#include <xercesc/util/PlatformUtils.hpp>
#include <xercesc/util/XMLString.hpp>
#include <xercesc/util/XercesVersion.hpp>

namespace fs = boost::filesystem;
namespace xs = xercesc;

namespace boost
{
namespace filesystem
{

// Return path when appended to a_from will resolve to same as a_to.
// Note: boost doesn't provide this functionality for now, see
// https://svn.boost.org/trac/boost/ticket/5897
std::string make_relative(path a_from, path a_to)
{
    a_from = canonical(a_from);
    a_to = canonical(a_to);
    const auto is_from_dir = is_directory(a_from);

    std::string ret;
    auto itr_from(a_from.begin());
    auto itr_to(a_to.begin());

    // Find common base.
    for (auto from_end(a_from.end()), to_end(a_to.end());
         itr_from != a_from.end() && itr_to != a_to.end() && *itr_from == *itr_to;
         ++itr_from, ++itr_to);

    // Navigate backwards in directory to reach previously found base.
    for (auto from_end(a_from.end()); itr_from != from_end; ++itr_from)
    {
        auto tmp_itr = itr_from;
        ++tmp_itr;

        if (is_from_dir || tmp_itr != from_end)
        {
            ret += "../";
        }
    }

    // Now navigate down the directory branch.
    for (auto to_end(a_to.end()); itr_to != to_end; ++itr_to)
    {
        ret += itr_to->string();

        auto tmp_itr = itr_to;
        ++tmp_itr;
        if (tmp_itr != to_end)
        {
            ret += "/";
        }
    }
    return ret;
}

} // filesystem namespace.
} // boost namespace.

namespace
{

auto xerces_string_deleter = [](XMLCh* p) { xs::XMLString::release(&p); };
auto plain_string_deleter = [](char* p) { xs::XMLString::release(&p); };

void print_help(const char* exe_name)
{
    std::cerr << "Usage: " << exe_name << " <schema-file>" << std::endl;
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
        xs::InputSource(xs::XMLPlatformUtils::fgMemoryManager),
        m_schema_path(schema_path)
    {
        std::unique_ptr<XMLCh, decltype(xerces_string_deleter)> xerces_path(
            xs::XMLString::transcode(m_schema_path.c_str()),
            xerces_string_deleter);

        setSystemId(xerces_path.get());
    }

    xs::BinInputStream* makeStream() const override
    {
        xs::BinFileInputStream* is(
            new (getMemoryManager())
            xs::BinFileInputStream(getSystemId(), getMemoryManager()));

        if (!is->getIsOpen())
        {
            delete is;
            throw std::runtime_error("Unable to open " + m_schema_path);
        }

        return is;
    }

private:
    std::string m_schema_path;
};

class SVErrorHandler: public xs::DOMErrorHandler
{
public:
    SVErrorHandler():
        m_cur_path(fs::current_path()),
        m_had_errors(false)
    {
    }

    bool handleError(const xs::DOMError &dom_error) override
    {
        xs::DOMLocator* loc = dom_error.getLocation();

        std::unique_ptr<char, decltype(plain_string_deleter)> uri(
            xs::XMLString::transcode(loc->getURI()),
            plain_string_deleter);

        if (std::string() != uri.get())
        {
            fs::path new_path(uri.get());

            std::cerr << fs::make_relative(m_cur_path, new_path);
        }
        else
        {
            std::cerr << "<>";
        }

        std::cerr << ':' << loc->getLineNumber() << ':'
                  << loc->getColumnNumber() << ": ";

        switch (dom_error.getSeverity())
        {
            case xs::DOMError::DOM_SEVERITY_WARNING:
            {
                std::cerr << "warning: ";
                break;
            }
            default:
            {
                m_had_errors = true;
                std::cerr << "error: ";
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
    fs::path m_cur_path;
    bool m_had_errors;
};

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

    // Xerces magic.
    XercesIniFiniGuard ini_fini_gu;

    SVInputSource input_source(abs_path.string());

    XMLCh const gLS[] = { xs::chLatin_L, xs::chLatin_S, xs::chNull };

    xs::DOMImplementationLS* impl(
        static_cast<xs::DOMImplementationLS*>(
            xs::DOMImplementationRegistry::getDOMImplementation(gLS)));

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

    xs::Wrapper4InputSource wrap(&input_source, false);
    parser->loadGrammar(wrap, xs::Grammar::SchemaGrammarType);
#endif

    if (eh.had_errors())
    {
        std::cerr << root_file << " is BAD" << std::endl;
        return 0;
    }

    std::cout << root_file << " is OK" << std::endl;
    return 0;
}
