// Distributed under the GPLv2 License; see accompanying file COPYING.

#pragma once

namespace V
{
namespace XMLSupport
{

template<typename XmlLoadContext>
class XmlDataConsumer
{
public: // functions

    explicit XmlDataConsumer(XmlLoadContext& context):
        _context(context)
    {
    }

    virtual ~XmlDataConsumer()
    {
    }

protected: // data

    XmlLoadContext& _context;
};

} // namespace XMLSupport
} // namespace V
