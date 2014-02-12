#! -*- encoding:utf-8 -*-
import urllib
import urllib2
import cookielib
import zipfile
import re
import os
import os.path
from bs4 import BeautifulSoup

def find_answer_urls(collection_url):
 	""" find the urls of the answers from the collection page(s)"""
 	prefix = 'http://www.zhihu.com'
 	urlpattern = re.compile(r'/question/\d{8}/answer/\d{8}')
 	html = urllib2.urlopen(collection_url).read()
 	# delete the repetitive urls
 	models = list(set(urlpattern.findall(html)))
 	urls = []
 	for model in models:
 		model = prefix + model
 		urls.append(model)
 	return urls

def collect_the_urls(collection_url):
 	"""collect the urls from the collection_url"""
	firstpage = urllib2.urlopen(collection_url).read()
	firstpage = BeautifulSoup(firstpage)
	# epub_title is the collection name
	epub_title = firstpage.title.string[:-11]
	# find out how many pages in the collection
	spans = firstpage.find(class_='zm-invite-pager')
	if type(spans) == type(None):
		spans = []
	else:
		spans = spans.find_all('span')
	# find all the question-answer urls in the collection
	pages = int()
	urls = []
	urls.append(find_answer_urls(collection_url))
	if len(spans) > 0:
		pages = int(spans[-2].get_text())
		for i in range(pages - 1):
			urls.append(find_answer_urls(collection_url + '?page=' + str(i + 1)))
		return (urls, epub_title)
	else:
		return (urls, epub_title)

def parse_html_into_epub(urls):
	answer_urls, epub_title = urls
	# can't deal with encoding/decoding problem, so the title can't generate automatically
	epub = zipfile.ZipFile(epub_title + '.epub', 'w')
	epub.writestr('mimetype', 'application/epub+zip')
	
	# write the css to the epub
	epub.writestr('stylesheet.css', '''
		body {line-height: 1.7;}
		#title {margin: 1em;}
		#author-info {margin: 1em; font-weight: bold;}
		#signature {margin-left: 1em;}
		.content {margin: 1em;}
  ''')
	
	epub.writestr('META-INF/container.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="Content.opf" media-type="application/oebps-package+xml" />
  </rootfiles>
</container>''')
	
	content_opf = '''<?xml version='1.0' encoding='utf-8'?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookID" version="2.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
      <dc:title>BookofKnowledge</dc:title>
      <dc:creator>zhihu.com</dc:creator>
      <dc:identifier id="BookID" opf:scheme="UUID">urn:uuid:Date2014-02-12</dc:identifier>
      <dc:language>zh-CN</dc:language>
      <dc:publisher>zhihu.com</dc:publisher>
      <meta name="cover" content="cover-image" />
	</metadata>
	<manifest>
		<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml" />
    	<item id="cover-image" href="Images/cover.jpg" media-type="image/jpeg"/>
    	<item id="css" href="stylesheet.css" media-type="text/css"/>
    	%(manifest)s
  	</manifest>
  	<spine toc="ncx">
    	%(spine)s
  	</spine>
</package>'''
	
	ncx = '''<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  	<head>
    	<meta name="dtb:uid" content="urn:uuid:Date2014-02-12"/>
    	<meta name="dtb:depth" content="1"/>
    	<meta name="dtb:totalPageCount" content="0"/>
    	<meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle>
    <text>BookofKnowledge</text>
  </docTitle>
  <navMap>
  	%(navPoint)s
  </navMap>
</ncx>'''
	manifest = ''
	spine = ''
	navPoint = ''
	i = 1
	for urllist in answer_urls:
		for url in urllist:
			answer_name = ''
			if i < 10:
				answer_name = 'Section00' + str(i) + '.html'
			elif i > 9 and i < 99:
				answer_name ='Section0' + str(i) + '.html'
			elif i >= 99:
				answer_name ='Section' + str(i) + '.html'
			else:
				raise ValueError()
			text = urllib2.urlopen(url).read()
			print 'We are downloading pages: ' + str(i)

			# close the br and the img tag, or the BeautifulSoup can't parse the page precisely
			br = re.compile('<br>')
			text = br.sub(r'<br />', text)
			img_list = re.findall(r'<img(.*?)>', text)
			for img in img_list:
				text = text.replace(img, img + ' /')

			# delete the redundant tags
			soup =  BeautifulSoup(text)
			webpage =  soup.find(id="zh-question-answer-wrap")
			for item in webpage.find_all("noscript"):
				item.decompose()

			# parse the page and get the contents we need
			title = soup.title.get_text()[:-5].encode('utf-8')
			author = webpage.find(class_="zm-item-answer-author-wrap").find_all("a")
			signature = webpage.find(class_="zu-question-my-bio")
			if len(author) >= 2:
				author = author[1].get_text().encode('utf-8')
			else:
				author = "知乎用户"
			if type(signature) != type(None):
				signature = signature['title'].encode('utf-8')
			else:
				signature = ""

			# download, write the images to the epub
			images = webpage.find_all(class_='lazy')
			if len(images) != 0:
				for img in images:
					if img.has_attr('data-original'):
						img_url = img['data-original']
						img_name = img_url[26:]
						img['src'] = '../Images/' + img_name
						manifest += '<item id="%(img_id)s" href="Images/%(img_name)s" media-type="application/xhtml+xml"/>' % {
						'img_id': img_url[26:35],
 						'img_name': img_name,
 						 }
 						img_file = urllib2.urlopen(img_url).read()
 						epub.writestr('Images/' + img_name, img_file)
 					else:
 						img_url = img['data-actualsrc']
 						img_name = img_url[26:]
						img['src'] = '../Images/' + img_name
						manifest += '<item id="%(img_id)s" href="Images/%(img_name)s" media-type="application/xhtml+xml"/>' % {
						'img_id': img_url[26:35],
 						'img_name': img_name,
 						 }
 						img_file = urllib2.urlopen(img_url).read()
 						epub.writestr('Images/' + img_name, img_file)

 			content = webpage.find(class_="zm-item-rich-text").find("div")
 			del content['class']
 			content['class'] = 'content'
 			content = content.encode('utf-8')
 			html = '''<?xml version="1.0" encoding="utf-8" standalone="no"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
  "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-CN">
<head>
 <link href="../stylesheet.css" rel="stylesheet" type="text/css" />
 <title>%s</title>
</head>
<body>
	<div id="title"><h2>%s</h2></div>
	<div id="author-info"><span id="author">%s</span><span id="signature">%s</span></div>
	%s
</body>
</html>'''%(title, title, author, signature, content)
			# write the epub
			epub.writestr('Text/' + answer_name, html)
			manifest += '<item id="%(answer_name)s" href="Text/%(answer_name)s" media-type="application/xhtml+xml"/>' % {
  			'answer_name': answer_name,
  			}
  			spine += '<itemref idref="%s" />' % answer_name
  			navPoint += '''<navPoint id="navpoint-%(order)s" playOrder="%(order)s"><navLabel><text>%(title)s</text></navLabel><content src="Text/%(answer_name)s"/></navPoint>''' % {
			'order': i,
			'answer_name': answer_name,
  			'title': title,
  			}
  			i += 1
  	if os.path.exists('cover.jpg'):
  		cover_image = open('cover.jpg', 'rb').read()
  		epub.writestr('Images/cover.jpg', cover_image)
	epub.writestr('Content.opf', content_opf % {
	'manifest': manifest,
	'spine': spine,
	#'epub_title': epub_title,
	})
	epub.writestr('toc.ncx', ncx % {
  'navPoint': navPoint,
  #'epub_title': epub_title,
  })

def init():
	collection_url = 'http://www.zhihu.com/collection/20328337'
	urls = collect_the_urls(collection_url)
	parse_html_into_epub(urls)

init()
