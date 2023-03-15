# RapidminerInstagramScraper
Rapidminer Process to extract Instagram Comments

Import the .rmp into Rapidminer

The process has been imported and tested on a Windows computer with Python 3 Anaconda andRapidminer 9.10. 
This means that the process can be used in both Mac and Windows. 

Installation Guide
Python 3 must first be installed, preferably Python 3 Anaconda. 
Install the requierments.txt filein the Python environment that is also specified in Rapidminer. 
On Mac the installation can be done in Terminal and on Windows in the Anaconda prompt. 
The installation command is install "pip -m install 'path to reuquierments.txt' ".

Use of Process
To use the process, the post code must be copied from the post URL and pasted into the postcode operator of post URL in the value field in the parameter area. 

For example, from the Post URL https://www.instagram.com/p/CTScuCwvscg, the value CTScuCwvscg must be specified in the operator. Then the user must create an Instagram profile WITHOUT two-factor authentication and then write the username and password in the same named operators. In the operator number of set must be specified a whole number, for example, 1000. 
If you want to translate emojis into text, you must write in the operator emojis conversion a yes and in the operator language for emoji editing you must  specify the language with de or en.
You can add more languages if you want. 
