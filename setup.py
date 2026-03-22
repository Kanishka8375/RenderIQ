from setuptools import setup, find_packages

setup(
    name="renderiq",
    version="0.1.0",
    description="AI Color Grade Transfer Tool",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "opencv-python>=4.8.0",
        "numpy>=1.24.0",
        "scipy>=1.11.0",
        "scikit-learn>=1.3.0",
        "colour-science>=0.4.0",
        "tqdm>=4.65.0",
        "Pillow>=10.0.0",
        "scenedetect[opencv]>=0.6.0",
    ],
    entry_points={
        "console_scripts": [
            "renderiq=cli:main",
        ],
    },
)
