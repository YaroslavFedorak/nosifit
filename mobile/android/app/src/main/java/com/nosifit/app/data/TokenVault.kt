package com.nosifit.app.data

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Where the sign-in token is kept between launches. */
interface TokenVault {
    fun read(): String?
    fun write(token: String?)
}

/**
 * Keeps the token encrypted with an AES key that never leaves the Android
 * Keystore. A copied preferences file is useless on another device.
 */
class KeystoreTokenVault(context: Context) : TokenVault {
    private val prefs = context.getSharedPreferences("nosifit_token", Context.MODE_PRIVATE)

    override fun read(): String? {
        val stored = prefs.getString(KEY_TOKEN, null) ?: return null
        return runCatching {
            val (iv, data) = stored.split(":").map { Base64.decode(it, Base64.NO_WRAP) }
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, iv))
            String(cipher.doFinal(data), Charsets.UTF_8)
        }.getOrElse {
            // Key gone (app data restored elsewhere, lock screen reset): sign in again.
            prefs.edit().remove(KEY_TOKEN).apply()
            null
        }
    }

    override fun write(token: String?) {
        if (token == null) {
            prefs.edit().remove(KEY_TOKEN).apply()
            return
        }
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val data = cipher.doFinal(token.toByteArray(Charsets.UTF_8))
        val encoded = listOf(cipher.iv, data).joinToString(":") { Base64.encodeToString(it, Base64.NO_WRAP) }
        prefs.edit().putString(KEY_TOKEN, encoded).apply()
    }

    private fun key(): SecretKey {
        val store = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        (store.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build(),
        )
        return generator.generateKey()
    }

    private companion object {
        const val KEYSTORE = "AndroidKeyStore"
        const val KEY_ALIAS = "nosifit_token_key"
        const val KEY_TOKEN = "token"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
    }
}

/** For tests and previews. */
class MemoryTokenVault(private var token: String? = null) : TokenVault {
    override fun read(): String? = token
    override fun write(token: String?) {
        this.token = token
    }
}
