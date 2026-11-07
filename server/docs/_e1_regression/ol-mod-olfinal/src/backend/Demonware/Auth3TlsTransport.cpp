#include "Auth3TlsTransport.hpp"

#include <algorithm>
#include <array>
#include <cctype>
#include <charconv>
#include <climits>
#include <limits>
#include <stdexcept>
#include <string>

#pragma warning(push, 0)
#include <openssl/bio.h>
#include <openssl/err.h>
#include <openssl/evp.h>
#include <openssl/rsa.h>
#include <openssl/ssl.h>
#include <openssl/x509.h>
#pragma warning(pop)

namespace
{
    std::string lower(std::string_view value)
    {
        std::string result(value);
        std::transform(result.begin(), result.end(), result.begin(), [](const unsigned char character)
        {
            return static_cast<char>(std::tolower(character));
        });
        return result;
    }

    std::string opensslError(const char *operation)
    {
        const auto code = ERR_get_error();
        std::array<char, 256> detail{};
        if (code)
            ERR_error_string_n(code, detail.data(), detail.size());
        return std::string(operation) + (code ? std::string(": ") + detail.data() : " failed");
    }

    void requireOpenSsl(const bool condition, const char *operation)
    {
        if (!condition)
            throw std::runtime_error(opensslError(operation));
    }

    EVP_PKEY *makeKey()
    {
        EVP_PKEY_CTX *context = EVP_PKEY_CTX_new_id(EVP_PKEY_RSA, nullptr);
        requireOpenSsl(context != nullptr, "EVP_PKEY_CTX_new_id");
        EVP_PKEY *key{};
        const auto initialized = EVP_PKEY_keygen_init(context);
        const auto configured = initialized > 0 ? EVP_PKEY_CTX_set_rsa_keygen_bits(context, 2048) : 0;
        const auto generated = configured > 0 ? EVP_PKEY_keygen(context, &key) : 0;
        EVP_PKEY_CTX_free(context);
        requireOpenSsl(generated > 0 && key, "EVP_PKEY_keygen");
        return key;
    }

    X509 *makeCertificate(EVP_PKEY *key, const std::string_view hostname)
    {
        X509 *certificate = X509_new();
        requireOpenSsl(certificate != nullptr, "X509_new");
        try
        {
            requireOpenSsl(ASN1_INTEGER_set(X509_get_serialNumber(certificate), 1) == 1,
                "ASN1_INTEGER_set");
            requireOpenSsl(X509_gmtime_adj(X509_getm_notBefore(certificate), 0) != nullptr,
                "X509_gmtime_adj(notBefore)");
            requireOpenSsl(X509_gmtime_adj(X509_getm_notAfter(certificate), 31536000L) != nullptr,
                "X509_gmtime_adj(notAfter)");
            requireOpenSsl(X509_set_pubkey(certificate, key) == 1, "X509_set_pubkey");

            auto *name = X509_get_subject_name(certificate);
            requireOpenSsl(name != nullptr, "X509_get_subject_name");
            requireOpenSsl(X509_NAME_add_entry_by_txt(name, "C", MBSTRING_ASC,
                reinterpret_cast<const unsigned char *>("SE"), -1, -1, 0) == 1, "X509 subject C");
            requireOpenSsl(X509_NAME_add_entry_by_txt(name, "O", MBSTRING_ASC,
                reinterpret_cast<const unsigned char *>("Hedgehogscience"), -1, -1, 0) == 1,
                "X509 subject O");
            requireOpenSsl(X509_NAME_add_entry_by_txt(name, "CN", MBSTRING_ASC,
                reinterpret_cast<const unsigned char *>(hostname.data()), static_cast<int>(hostname.size()), -1, 0) == 1,
                "X509 subject CN");
            requireOpenSsl(X509_set_issuer_name(certificate, name) == 1, "X509_set_issuer_name");
            // Match Ayria's 2019 IHTTPSServer exactly. CODOL's legacy verifier
            // rejects the otherwise valid v3/SHA-256 certificate during Auth3.
            requireOpenSsl(X509_sign(certificate, key, EVP_sha1()) > 0, "X509_sign");
            return certificate;
        }
        catch (...)
        {
            X509_free(certificate);
            throw;
        }
    }
}

namespace AlwaysofflineRe::Demonware
{
    struct Auth3TlsTransport::Impl
    {
        AuthSession &session;
        std::string hostname;
        Diagnostic diagnostic;
        Auth3Protocol protocol;
        SSL_CTX *context{};
        SSL *ssl{};
        std::string plaintext;

        Impl(
            AuthSession &authSession,
            std::string host,
            Diagnostic callback,
            PlayerIdentityStore *identityStore)
            : session(authSession), hostname(std::move(host)),
              diagnostic(std::move(callback)), protocol(session, identityStore)
        {
            context = SSL_CTX_new(TLS_server_method());
            requireOpenSsl(context != nullptr, "SSL_CTX_new");
            try
            {
                SSL_CTX_set_security_level(context, 0);
                requireOpenSsl(SSL_CTX_set_min_proto_version(context, TLS1_VERSION) == 1,
                    "SSL_CTX_set_min_proto_version");
                requireOpenSsl(SSL_CTX_set_cipher_list(context, "ALL:@SECLEVEL=0") == 1,
                    "SSL_CTX_set_cipher_list");

                EVP_PKEY *key = makeKey();
                X509 *certificate{};
                try
                {
                    certificate = makeCertificate(key, hostname);
                    requireOpenSsl(SSL_CTX_use_certificate(context, certificate) == 1,
                        "SSL_CTX_use_certificate");
                    requireOpenSsl(SSL_CTX_use_PrivateKey(context, key) == 1,
                        "SSL_CTX_use_PrivateKey");
                    requireOpenSsl(SSL_CTX_check_private_key(context) == 1,
                        "SSL_CTX_check_private_key");
                }
                catch (...)
                {
                    X509_free(certificate);
                    EVP_PKEY_free(key);
                    throw;
                }
                X509_free(certificate);
                EVP_PKEY_free(key);
                reset();
            }
            catch (...)
            {
                SSL_CTX_free(context);
                context = nullptr;
                throw;
            }
        }

        ~Impl()
        {
            SSL_free(ssl);
            SSL_CTX_free(context);
        }

        void report(const std::string_view message) const
        {
            if (diagnostic)
                diagnostic(message);
        }

        void reset()
        {
            SSL_free(ssl);
            ssl = SSL_new(context);
            requireOpenSsl(ssl != nullptr, "SSL_new");
            BIO *read = BIO_new(BIO_s_mem());
            BIO *write = BIO_new(BIO_s_mem());
            if (!read || !write)
            {
                BIO_free(read);
                BIO_free(write);
                SSL_free(ssl);
                ssl = nullptr;
                throw std::runtime_error(opensslError("BIO_new"));
            }
            BIO_set_nbio(read, 1);
            BIO_set_nbio(write, 1);
            SSL_set_bio(ssl, read, write);
            SSL_set_accept_state(ssl);
            plaintext.clear();
        }

        void queuePlaintext(const std::string_view data)
        {
            std::size_t offset{};
            while (offset < data.size())
            {
                std::size_t written{};
                const auto result = SSL_write_ex(ssl, data.data() + offset, data.size() - offset, &written);
                if (result != 1)
                {
                    const auto error = SSL_get_error(ssl, result);
                    if (error == SSL_ERROR_WANT_READ || error == SSL_ERROR_WANT_WRITE)
                        continue;
                    throw std::runtime_error(opensslError("SSL_write_ex"));
                }
                offset += written;
            }
        }

        void processHttp()
        {
            while (true)
            {
                const auto headerEnd = plaintext.find("\r\n\r\n");
                if (headerEnd == std::string::npos)
                    return;
                const auto firstLineEnd = plaintext.find("\r\n");
                if (firstLineEnd == std::string::npos || firstLineEnd > headerEnd)
                    throw std::runtime_error("malformed Auth3 HTTP request line");
                const auto requestLine = plaintext.substr(0, firstLineEnd);
                if (!requestLine.starts_with("POST /auth/"))
                    throw std::runtime_error("unexpected Auth3 HTTP target");

                std::size_t contentLength{};
                auto cursor = firstLineEnd + 2;
                while (cursor < headerEnd)
                {
                    const auto lineEnd = plaintext.find("\r\n", cursor);
                    const auto line = std::string_view(plaintext).substr(cursor, lineEnd - cursor);
                    const auto separator = line.find(':');
                    if (separator != std::string_view::npos && lower(line.substr(0, separator)) == "content-length")
                    {
                        auto value = line.substr(separator + 1);
                        while (!value.empty() && value.front() == ' ') value.remove_prefix(1);
                        const auto converted = std::from_chars(
                            value.data(), value.data() + value.size(), contentLength);
                        if (converted.ec != std::errc{})
                            throw std::runtime_error("invalid Auth3 Content-Length");
                    }
                    cursor = lineEnd + 2;
                }

                const auto messageSize = headerEnd + 4 + contentLength;
                if (plaintext.size() < messageSize)
                    return;
                const auto body = plaintext.substr(headerEnd + 4, contentLength);
                plaintext.erase(0, messageSize);
                const auto result = protocol.authenticate(body);
                report("AUTH3_CAPTURE request=" + std::string(body));
                report("AUTH3_CAPTURE response=" + result.json);
                report(std::string("Authenticated user ") + result.username + " (" +
                    std::to_string(result.userId) + ") for title " + std::to_string(result.titleId) + '.');
                queuePlaintext(Auth3Protocol::httpResponse(result.json));
            }
        }

        void processTls()
        {
            if (!SSL_is_init_finished(ssl))
            {
                const auto result = SSL_do_handshake(ssl);
                if (result != 1)
                {
                    const auto error = SSL_get_error(ssl, result);
                    if (error != SSL_ERROR_WANT_READ && error != SSL_ERROR_WANT_WRITE)
                        throw std::runtime_error(opensslError("SSL_do_handshake"));
                }
            }
            if (!SSL_is_init_finished(ssl))
                return;

            std::array<char, 4096> buffer{};
            while (true)
            {
                std::size_t read{};
                const auto result = SSL_read_ex(ssl, buffer.data(), buffer.size(), &read);
                if (result == 1)
                {
                    plaintext.append(buffer.data(), read);
                    processHttp();
                    continue;
                }
                const auto error = SSL_get_error(ssl, result);
                if (error == SSL_ERROR_WANT_READ || error == SSL_ERROR_WANT_WRITE)
                    return;
                if (error == SSL_ERROR_ZERO_RETURN)
                {
                    reset();
                    return;
                }
                throw std::runtime_error(opensslError("SSL_read_ex"));
            }
        }
    };

    Auth3TlsTransport::Auth3TlsTransport(
        AuthSession &session,
        std::string hostname,
        Diagnostic diagnostic,
        PlayerIdentityStore *identityStore)
        : impl_(std::make_unique<Impl>(
            session, std::move(hostname), std::move(diagnostic), identityStore))
    {
    }

    Auth3TlsTransport::~Auth3TlsTransport() = default;

    void Auth3TlsTransport::reset()
    {
        impl_->reset();
    }

    void Auth3TlsTransport::receive(const std::span<const std::uint8_t> encrypted)
    {
        if (encrypted.empty() || encrypted.size() > static_cast<std::size_t>((std::numeric_limits<int>::max)()))
            return;
        const auto written = BIO_write(SSL_get_rbio(impl_->ssl), encrypted.data(), static_cast<int>(encrypted.size()));
        if (written != static_cast<int>(encrypted.size()))
            throw std::runtime_error(opensslError("BIO_write"));
        impl_->processTls();
    }

    std::vector<std::uint8_t> Auth3TlsTransport::takeOutput(const std::size_t limit)
    {
        if (!limit)
            return {};
        std::vector<std::uint8_t> output(limit);
        const auto read = BIO_read(
            SSL_get_wbio(impl_->ssl), output.data(), static_cast<int>(std::min<std::size_t>(limit, INT_MAX)));
        if (read <= 0)
            return {};
        output.resize(static_cast<std::size_t>(read));
        return output;
    }
}
