from setuptools import setup, find_packages

setup(
    name="raps-dashboard",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'nba_api>=1.2.1',
        'polars>=0.20.2',
        'streamlit>=1.29.0',
        'scikit-learn>=1.3.0',
        'plotly>=5.18.0',
        'pyyaml>=6.0.1',
        'joblib>=1.3.2',
    ],
)