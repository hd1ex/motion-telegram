for lang in de en ; do
    msgfmt -o locales/$lang/LC_MESSAGES/base.mo locales/$lang/LC_MESSAGES/base
done
