"""Fa firmare la build release con la chiave letta dalle variabili d'ambiente ANDROID_KEYSTORE_*.
Senza queste variabili usa la firma di debug (build di prova)."""
import sys

path = sys.argv[1]
s = open(path, encoding="utf-8").read()
old = "    buildTypes {\n        release {\n            signingConfig signingConfigs.debug\n"
new = """    signingConfigs {
        release {
            def ksPath = System.getenv("ANDROID_KEYSTORE_PATH")
            if (ksPath) {
                storeFile file(ksPath)
                storePassword System.getenv("ANDROID_KEYSTORE_PASSWORD")
                keyAlias System.getenv("ANDROID_KEY_ALIAS")
                keyPassword System.getenv("ANDROID_KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            signingConfig System.getenv("ANDROID_KEYSTORE_PATH") ? signingConfigs.release : signingConfigs.debug
"""
assert s.count(old) == 1, "blocco buildTypes non trovato nel build.gradle del template"
open(path, "w", encoding="utf-8").write(s.replace(old, new))
print("build.gradle aggiornato")
