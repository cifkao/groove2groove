import setuptools

setuptools.setup(
    name='groove2groove',
    author='Ondřej Cífka',
    description='Music style transfer and style translation models',
    url='https://github.com/cifkao/groove2groove',
    python_requires='>=3.6',
    install_requires=[
        'scipy'
    ],
    extras_require={
        'gpu': 'museflow[gpu] @ git+https://github.com/cifkao/museflow',
        'nogpu': 'museflow[nogpu] @ git+https://github.com/cifkao/museflow',
    },
    packages=setuptools.find_packages()
)
