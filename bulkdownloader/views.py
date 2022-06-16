# Python script : Wikimedia Commons Bulk Downloader By Category
import requests
import aiohttp
import asyncio
import aiofiles
from bs4 import BeautifulSoup
import urllib
import json
import os
import time
from django.shortcuts import render
from bulkdownloader import config
from flask import request
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger




#from django.conf import Settings

# Base config information imported from config.py
#from config import category
#from config import max_records
#from config import limit


max_records = -1
limit = 500

# Commons API URL
wc_url = "https://commons.wikimedia.org/w/api.php"

# Print empty line
def print_line():
	print("-"*80)

s_time = time.time()
	
print_line()


# Limit value should be less than or equal to 500
if (limit > 500):
	limit = 500

# Validate the max_records and limit value
if (max_records != -1 and max_records < limit):
	limit = max_records

# Getting next offset value from json response
def get_next_offset(res):
	if ("continue" in res and "cmcontinue" in res["continue"]):
		return res["continue"]["cmcontinue"]
	return None

# def login(request):
#     return render(request, 'wikimedia_page.html')

def home(request):

    if request.method == 'POST':
        page = request.GET.get('page', 1)
        if 'search' in request.POST or request.POST.get('search_value'):
            page = request.GET.get('page', 1)
            category = request.POST.get('search_value')
        if 'download' in request.POST:
            category = request.POST.get('search_value')
            page = request.GET.get('page', 1)
            flag = 1
            final_files_list = request.POST.getlist('final_list[]')
            if request.POST.getlist('file_name[]'):
                final_files_list = request.POST.getlist('file_name[]')
            else:
                final_files_list=final_files_list
            asyncio.run(fetch_download_links_and_download_file(final_files_list,category))
            messages.success(request, 'Files downloaded successfully!', extra_tags='alert')
    else:
        category = "CHECK"
    

	# Setting base params
    next_offset = ""

    #ses = requests.Session()
    d,count=fetch_all_file_names_in_category(next_offset, category)


    filtered_list = []
    for file_name in d:
        if (file_name.startswith("File:")):
            filtered_list.append(file_name)

    final_files_list = list(set(filtered_list))
    
    
    page = request.GET.get('page', 1)
    paginator = Paginator(d, 10)
    try:
        d = paginator.page(page)
    except PageNotAnInteger:
        d = paginator.page(1)
    except EmptyPage:
        d = paginator.page(paginator.num_pages)
    params_data = {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": "Category:Files uploaded by spell4wiki",
            "cmlimit": 500,
            "cmsort": "timestamp",
            
            }
    R = requests.get(wc_url,params = params_data)
    #R = S.get(url=URL, params=PARAMS)
    DATA = R.json()
    PAGES = DATA["query"]["categorymembers"]
    cat_list=[]
    for i in PAGES:
        if  not (i['title'].startswith("File:")):
            c=i['title'].split()
            cat_list.append(c[-1])
    return render(request, 'home.html', {'d': d,'count': count, 'search': category,'final_list':final_files_list,'categories':cat_list})

# Fetching all file names in particular category
def fetch_all_file_names_in_category(next_offset, category):
    category = config.category + str(category)
    file_names = []
    ses = requests.Session()
    while next_offset != None and (len(file_names) < max_records or max_records == -1):
        #req = ses.get(url=settings.wc_url, params=params_data)
        params_data = {
        "action": "query",
        "format": "json",
        "list": "categorymembers",
        "cmtitle": category,
        "cmlimit": limit,
        "cmsort": "timestamp",
        "cmdir": "desc"
        }
        req = requests.get(wc_url,params = params_data)
        d = req.json()
        next_offset = get_next_offset(d)
        itemlist = d["query"]["categorymembers"]

        for item in itemlist:
            file_names.append(item["title"])

        if (next_offset != None):
            bal_count = max_records - len(file_names)
        if (max_records != -1 and bal_count < limit):
            params_data["cmlimit"] = bal_count
        if (next_offset != None):
            params_data["cmcontinue"] = next_offset
        fetch_all_file_names_in_category(next_offset, category)
    
    return file_names,len(file_names)

# Getting download url from commons html page
async def get_file_download_link(session, file_name):
	url = "https://commons.wikimedia.org/wiki/"+file_name
	try:		
		async with session.get(url) as response:
			html_body = await response.read()
			soup = BeautifulSoup(html_body, "html.parser")
			media = soup.findAll("div", attrs={"class":"fullMedia"})
			dl = media[0].find('a').get("href")
			f_dl = urllib.parse.unquote(dl)
			# print(file_name + " => " + f_dl)
			return f_dl

	except BaseException as e:
		print_line()
		print("An exception occurred " + file_name)
		print(e)
		

# Download file from commons download link 
async def save_downloaded_file(session, dl, index, total_links_count,category=""):
    try:
        async with session.get(dl, allow_redirects=True) as audio_request:
            if audio_request.status == 200:
                d_filename = urllib.parse.unquote(dl).split("/")[-1]
                # print(str(index+1) + "/" + str(total_links_count) + " => " + d_filename)
                dest_folder = category.replace(" ", "_")
                file_path = os.path.join(dest_folder, d_filename)
                f = await aiofiles.open(file_path, mode='wb')
                await f.write(await audio_request.read())
                await f.close()

    except BaseException as e:
        print_line()
        print("An exception occurred while downloading " + dl)
        print(e)


# Task to Start getting download links then download files from download links
download_links = []
async def fetch_download_links_and_download_file(final_files_list,category):
    print_line()
    async with aiohttp.ClientSession() as session:
        tasks = []
        print("Fetching download links....")
        new_final_files_list = []
        for index, f in enumerate(final_files_list):
            task = asyncio.ensure_future(get_file_download_link(session, f))
            tasks.append(task)
			
        temp_download_links = await asyncio.gather(*tasks)
        download_links = list(filter(None, temp_download_links)) # Filter valid links
        print("Total time for Scraping download links: %.2f secs" % (time.time() - s_time))
        total_links_count = len(download_links)
        print("Total download links: " + str(total_links_count))
		
		
		# Start Download Task
		# Download file from commons download link 
		
		# create folder if it does not exist
        dest_folder = category.replace(" ", "_")
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)
		
        print_line()
        print("Please wait %s files are Downloading...." % (str(total_links_count))) 
        download_tasks = []
        for index, dl in enumerate(download_links):
            download_task = asyncio.ensure_future(save_downloaded_file(session, dl, index, total_links_count,category))
            download_tasks.append(download_task)
        download_files = await asyncio.gather(*download_tasks)
        print("Total time for Download files : %.2f secs" % (time.time() - s_time))
        print("Total downloaded files: " + str(len(download_files)))
        print_line()

        print("All files are downloaded under: " + dest_folder)
        print_line()


