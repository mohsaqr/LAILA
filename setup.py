from setuptools import setup

setup(
    name='LAILA',

    py_modules=["app","config","API_Settings","wsgi"],  # Only include your main script/module
    packages=["model","views","static/css","static/js","db","prompts"],
    install_requires=open("requirements.txt").read().splitlines(),
    include_package_data=True,
    package_data={
        "": ["*.html", "*.txt", "*.json", "*.css", "*.js"],
    },
)