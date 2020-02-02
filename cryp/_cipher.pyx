from cpython.bytes cimport *

cdef extern from "Python.h":
    object PyUnicode_FromString(char *u)

cdef extern from "openssl/err.h":
    unsigned long ERR_get_error()
    char *ERR_error_string(unsigned long e, char *str)
    char *ERR_reason_error_string(unsigned long e)
    void ERR_load_crypto_strings()

cdef extern from "openssl/evp.h":
    ctypedef struct EVP_CIPHER_CTX
    ctypedef struct EVP_CIPHER

    EVP_CIPHER_CTX *EVP_CIPHER_CTX_new()
    void EVP_CIPHER_CTX_free(EVP_CIPHER_CTX *)
    int EVP_EncryptInit_ex(EVP_CIPHER_CTX *ctx, const EVP_CIPHER *typ, void *eng,
                unsigned char *key, unsigned char *iv)
    int EVP_EncryptFinal_ex(EVP_CIPHER_CTX *ctx, unsigned char *out,
                int *outl)
    int EVP_EncryptUpdate(EVP_CIPHER_CTX *ctx, unsigned char *out,
                int *outl, unsigned char *inp, int inl)
    int EVP_DecryptInit_ex(EVP_CIPHER_CTX *ctx, const EVP_CIPHER *typ, void *eng,
                unsigned char *key, unsigned char *iv)
    int EVP_DecryptFinal_ex(EVP_CIPHER_CTX *ctx, unsigned char *out,
                int *outl)
    int EVP_DecryptUpdate(EVP_CIPHER_CTX *ctx, unsigned char *out,
                int *outl, unsigned char *inp, int inl)
    int EVP_CIPHER_CTX_set_key_length(EVP_CIPHER_CTX *x, int keylen)
    int EVP_CIPHER_CTX_set_padding(EVP_CIPHER_CTX *x, int padding)
    const EVP_CIPHER *EVP_aes_128_cbc()
    const EVP_CIPHER *EVP_aes_256_cbc()
    const EVP_CIPHER *EVP_bf_cbc()
    int EVP_CIPHER_block_size(const EVP_CIPHER *)



cdef char *defaultiv = "\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0"
ERR_load_crypto_strings()

cdef int check(int value) except -1:
    cdef object err
    if not value:
        raise ValueError(PyUnicode_FromString(
            ERR_reason_error_string(ERR_get_error())))

cdef object _encrypt(const EVP_CIPHER *ciph,
    unsigned char *data, int dlen, unsigned char *key, int klen):
    cdef int tmp_len = 0
    cdef int out_len = 0
    cdef output = PyBytes_FromStringAndSize(NULL, dlen)
    cdef unsigned char *out = <unsigned char *>PyBytes_AsString(output)
    cdef EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new()
    if not ctx:
        raise MemoryError()
    try:
        check(EVP_EncryptInit_ex(ctx, ciph, NULL, NULL, NULL))
        check(EVP_CIPHER_CTX_set_key_length(ctx, klen))
        check(EVP_CIPHER_CTX_set_padding(ctx, 0))
        check(EVP_EncryptInit_ex(ctx, NULL, NULL,
            key, <unsigned char *>defaultiv))
        check(EVP_EncryptUpdate(ctx, out, &out_len, data, dlen))
        tmp_len += out_len
        check(EVP_EncryptFinal_ex(ctx, out+out_len, &out_len))
    finally:
        EVP_CIPHER_CTX_free(ctx)
    tmp_len += out_len
    assert tmp_len == len(output), (tmp_len, len(output), dlen)
    return output

def aes_encrypt(data, key):
    return _encrypt(EVP_aes_256_cbc(),
        data, len(data), key, len(key))

def bf_encrypt(data, key):
    return _encrypt(<const EVP_CIPHER *>EVP_bf_cbc(),
        data, len(data), key, len(key))

cdef object _decrypt(const EVP_CIPHER *ciph,
    unsigned char *data, int dlen, unsigned char *key, int klen):
    cdef int tmp_len = 0
    cdef int out_len = 0
    cdef output = PyBytes_FromStringAndSize(NULL, dlen)
    cdef unsigned char *out = <unsigned char *>PyBytes_AsString(output)
    cdef EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new()
    try:
        check(EVP_DecryptInit_ex(ctx, ciph, NULL, NULL, NULL))
        check(EVP_CIPHER_CTX_set_key_length(ctx, klen))
        check(EVP_CIPHER_CTX_set_padding(ctx, 0))
        check(EVP_DecryptInit_ex(ctx, NULL, NULL,
            key, <unsigned char *>defaultiv))
        check(EVP_DecryptUpdate(ctx, out, &out_len, data, dlen))
        tmp_len += out_len
        check(EVP_DecryptFinal_ex(ctx, out+out_len, &out_len))
    finally:
        EVP_CIPHER_CTX_free(ctx)
    tmp_len += out_len
    assert tmp_len == len(output), (tmp_len, len(output))
    return output

def aes_decrypt(data, key):
    return _decrypt(<const EVP_CIPHER *>EVP_aes_256_cbc(),
        data, len(data), key, len(key))

def bf_decrypt(data, key):
    return _decrypt(<const EVP_CIPHER *>EVP_bf_cbc(),
        data, len(data), key, len(key))
