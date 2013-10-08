#include <memory>
#include <iostream>

#include <boost/filesystem/path.hpp>
#include <boost/filesystem/operations.hpp>

#include <xercesc/dom/DOM.hpp>
#include <xercesc/framework/Wrapper4InputSource.hpp>
#include <xercesc/sax/ErrorHandler.hpp>
#include <xercesc/sax/InputSource.hpp>
#include <xercesc/validators/common/Grammar.hpp>
#include <xercesc/util/PlatformUtils.hpp>
#include <xercesc/util/XercesVersion.hpp>

namespace
{

void print_help(const char* exe_name)
{
    std::cerr << "Usage: " << exe_name << " <schema-file>" << std::endl;
}

class XercesIniFiniGuard
{
public:
    XercesIniFiniGuard()
    {
        xercesc::XMLPlatformUtils::Initialize();
    }

    ~XercesIniFiniGuard()
    {
        xercesc::XMLPlatformUtils::Terminate();
    }
};

class SVInputSource: public xercesc::InputSource
{
public:
    SVInputSource(const boost::filesystem::path& schema_path)
    {

    }

    xercesc::BinInputStream* makeStream() const override
    {
        return nullptr;
    }
};

class SVErrorHandler: public xercesc::DOMErrorHandler
{
public:
    bool handleError(const xercesc::DOMError &dom_error) override
    {
        return true;
    }
};

} // anonymous

int main(int argc, char *argv[])
{
    namespace fs = boost::filesystem;
    namespace xs = xercesc;

    if (argc != 2)
    {
        print_help(argv[0]);
        return 1;
    }

    std::cout << argv[1] << std::endl;
    fs::path abs_path(fs::system_complete(argv[1]));
    std::cout << abs_path.string() << std::endl;
    abs_path.normalize();
    std::cout << abs_path.string() << std::endl;

    SVInputSource input_source(abs_path);

    XMLCh const gLS[] = { xs::chLatin_L, xs::chLatin_S, xs::chNull };

    // Xerces magic.
    XercesIniFiniGuard ini_fini_gu;

    xs::DOMImplementationLS* impl(
        static_cast<xs::DOMImplementationLS*>(
            xs::DOMImplementationRegistry::getDOMImplementation(gLS)));

#if XERCES_VERSION_MAJOR >= 3
    std::unique_ptr<xs::DOMLSParser> parser(
        impl->createLSParser(xs::DOMImplementationLS::MODE_SYNCHRONOUS, 0));

    xs::DOMConfiguration* conf(parser->getDomConfig());

    conf->setParameter(xs::XMLUni::fgDOMComments, false);
    conf->setParameter(xs::XMLUni::fgDOMDatatypeNormalization, true);
    conf->setParameter(xs::XMLUni::fgDOMEntities, false);
    conf->setParameter(xs::XMLUni::fgDOMNamespaces, true);
    conf->setParameter(xs::XMLUni::fgDOMValidate, true);
    conf->setParameter(xs::XMLUni::fgDOMElementContentWhitespace, false);
    conf->setParameter(xs::XMLUni::fgXercesSchema, true);
    conf->setParameter(xs::XMLUni::fgXercesSchemaFullChecking, true);
    conf->setParameter(xs::XMLUni::fgXercesValidationErrorAsFatal, false);
#if XERCES_VERSION_MINOR >= 1
    conf->setParameter(xs::XMLUni::fgXercesHandleMultipleImports, true);
#endif

    SVErrorHandler eh;
    conf->setParameter(xs::XMLUni::fgDOMErrorHandler, &eh);

    xs::Wrapper4InputSource wrap(&input_source, false);
    parser->loadGrammar(&wrap, xs::Grammar::SchemaGrammarType);
#else
    std::unique_ptr<xs::DOMBuilder> parser(
        impl->createDOMBuilder(xs::DOMImplementationLS::MODE_SYNCHRONOUS, 0));

    parser->setFeature(xs::XMLUni::fgDOMComments, false);
    parser->setFeature(xs::XMLUni::fgDOMDatatypeNormalization, true);
    parser->setFeature(xs::XMLUni::fgDOMEntities, false);
    parser->setFeature(xs::XMLUni::fgDOMNamespaces, true);
    parser->setFeature(xs::XMLUni::fgDOMValidation, true);
    parser->setFeature(xs::XMLUni::fgDOMWhitespaceInElementContent, false);
    parser->setFeature(xs::XMLUni::fgXercesSchema, true);
    parser->setFeature(xs::XMLUni::fgXercesSchemaFullChecking, true);
    parser->setFeature(xs::XMLUni::fgXercesValidationErrorAsFatal, false);

    SVErrorHandler eh;
    parser->setErrorHandler(&eh);

    xs::Wrapper4InputSource wrap(&input_source, false);
    parser->loadGrammar(wrap, xs::Grammar::SchemaGrammarType);
#endif

    return 0;
}
