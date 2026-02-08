import os
import random

import yaml

from src.config import DEFAULT_LANGUAGE

translations = {}
translations_dir = 'assets/translations'


def load_translations():
    for filename in os.listdir(translations_dir):
        if not filename.endswith('.yaml'):
            continue

        with open(os.path.join(translations_dir, filename), encoding='utf-8') as file:
            content = yaml.safe_load(file)

        language_code = filename.split('.')[0]
        translations[language_code] = content


def translate(key: str, language: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    template = translations.get(language, translations.get(DEFAULT_LANGUAGE, {})).get(key, key)

    if isinstance(template, list):
        template = random.choice(template)

    for key, value in kwargs.items():
        if not value:
            placeholder = f'{{{key}}}'
            template = '\n'.join(line for line in template.splitlines() if line != placeholder)

    return template.format(**kwargs).strip()


def get_all_translations(key: str) -> list[str]:
    return [language.get(key) for language in translations.values()]


_ = translate
load_translations()
