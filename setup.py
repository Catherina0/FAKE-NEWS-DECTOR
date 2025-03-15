import os
from setuptools import setup, find_packages

setup(
    name="news_credibility",
    version="0.2.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
        "jieba>=0.42.1",
        "termcolor>=1.1.0",
        "urllib3>=1.26.0",
        "beautifulsoup4>=4.9.0",
        "langchain-community>=0.0.1",
        "python-dotenv>=0.19.0",
    ],
    extras_require={
        "full": [
            "serpapi>=0.1.0",
            "colorama>=0.4.4",
        ],
    },
    entry_points={
        "console_scripts": [
            "news-credibility=news_credibility:main",
        ],
    },
    author="News Credibility Team",
    author_email="example@example.com",
    description="一个分析新闻可信度的工具",
    long_description=open("README.md", encoding="utf-8").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    url="https://github.com/example/news-credibility",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
) 