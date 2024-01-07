# webnovel2epub

This set of Python scripts are aimed at downloading chapters from novels available on webnovel.com and convert them into the EPUB format.

## Getting Started

To run this script, you will need to have a Python 3 installation, which you can find [here](https://www.python.org/downloads/ "Python Download Link").

Additionally, you will need `chromedriver`, which you can find [here](http://chromedriver.chromium.org/ "chromedriver Download Link").
The easiest way to install `chromedriver` is through a package manager:

- Mac OS: `brew cask install chromedriver`
- Linux: `npm -g install chromedriver`

Otherwise, download it from the website, unpack the ZIP file and place the executable `chromedriver` somewhere in your PATH.

It is also possible to use `geckodriver` (ie. Firefox), although for now, only through the `--with-firefox-data` command line argument (or by manually editting the `webnovel2epub.py` file).

### Features

- Download and save your favorite novels from webnovel.com into an EPUB file.
- Automatically adds some metadata like author, title, series names and cover if available.
- Grabs the list of Novel as well as available chapters and metadata in real-time.
- Possibility to merge new chapters into an old EPUB file

### Prerequisites

This script was developed while using Python 3.7. It should however also work with older Python 3 versions.
Also, you'll need a modified version of ebooklib, which you can find [here](https://github.com/Takishima/ebooklib), selenium and tqdm. To get them just open a terminal and run:
```
pip install git+https://github.com/Takishima/ebooklib.git@master selenium tqdm pillow
```

Note that on some Linux installations, you might need to install `libxml2-dev` and `libxmlsec1-dev`. E.g.
```
sudo apt-get install libxml2-dev libxmlsec1-dev
```

### Usage

Before running the script make sure you that `chromedriver` can be found somewhere in your PATH.

Navigate to the folder using the terminal then enter:
```
python3 webnovel2epub.py --help
```
This should display a help message showing you all the available options.

If you did not add Python to the PATH variable during the installation or afterwards you might need to specify the Python executable path explicitly:

```
path/where/you/installed/python3 webnovel2ebook.py --help
```

#### Basic usage

Downloading a novel can be as simple as running:
```
python3 webnovel2epub.py
```
The script will then lead you to finding a novel by browsing the various categories on webnovel.com, allowing you to choose a title and then downloading all the relevant metadata and chapter data. After it finishes, you should find a new EPUB file in the folder you launched the command from.

If you possess a webnovel.com login (for now only login with email is supported), you can allow the script to login into your account, which would then allow you to access all the chapters you have unlocked. For that, you might want to take a look at the following command line options:
- `--with-credentials`
- `--with-username` and `--with-password`

#### More advanced usage

The script can be also completely automated. For example:
```
python webnovel2ebook.py --with-credentials webnovel.auth \
  --with-chapter-start 1000 --with-chapter-end -1 \
  --with-category video-games --with-title avatar
```
which would download chapters 1000 and above from _The King's Avatar_ (at the time of writing that novel is the only one containing the word _avatar_ in the top selection of video games novels).

Have a look at the help message for more information on the possibilities of automation.

### ToDo list

Nothing yet. If you encounter some problems or have some ideas for improving the scripts, please create an issue or contact me.

## License

This project is licensed under the Mozilla Public License Version 2.0 - see the [LICENSE](LICENSE) file for details

## Acknowledgments

This small project originated from me tinkering with the [webnovel2ebook](https://github.com/seba11998/webnovel2ebook/) code from seba11998.
