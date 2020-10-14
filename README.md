## Browser URL Fetcher
=====================================

Fetches the URL History of the browser

> python3.8 geturls.py -h

```
usage: geturls.py [-h] -b {firefox,chrome,opera,brave,edge} [-c COUNT] [-d]
                  [-l ROWLENGTH] [-t FROMTIME]

Get running browser history from sqlite database

optional arguments:
  -h, --help            show this help message and exit
  -b {firefox,chrome,opera,brave,edge}, --browser {firefox,chrome,opera,brave,edge}
  -c COUNT, --count COUNT
                        Doesn't work with --fromtime
  -d, --dont-copy
  -l ROWLENGTH, --rowlength ROWLENGTH
  -t FROMTIME, --fromtime FROMTIME
                        YYYY-MM-DDTHH:MM:SS
```