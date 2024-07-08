from setuptools import find_packages, setup

setup(
    name="realestate",
    packages=find_packages(exclude=["realestate_tests"]),
    install_requires=[
        "dagster==1.6.8",
        "dagster-pandas",
        "dagstermill",
        "notebook",
        "dagster-aws",
        "dagster-postgres",
        "dagster-webserver",
        "dagster-deltalake",
        "dagster-deltalake-pandas",
        "pyarrow",
        "pandas",
        "boto3",
        "pandasql",
        "pyyaml",
        "numpy",
        "seaborn",
        "folium",
        "ijson",
        "koalas",
        "scipy",
        "matplotlib",
        "scikit-learn",
        "bs4",
        "pandasql",
    ],
    extras_require={"dev": ["dagster-webserver", "pytest"]},
)

