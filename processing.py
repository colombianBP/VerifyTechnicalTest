import re
import os
import sys
import json
import pickle
import zipfile
import warnings
import textdistance
import numpy as np
import pandas as pd
from veryfi import Client
from itertools import chain

#comment this line to enter credentials manually
args = sys.argv

##### Uncomment these lines and write your credentials

#client_id = ''
#client_secret = ''
#username = ''
#api_key = ''

#args=[client_id,client_secret,username,api_key]

##### Uncomment these lines and write your credentials


# Use default .zip file or take from args 
if len(args)==4:
    # this line can also be changed to edit your input zip file
    zip_file_path = 'documents_to_process.zip'
elif len(args)==5:
    zip_file_path = args[4]
else:
    raise Exception('4 or 5 arguments expected, recieved '+len(args))

#output file, this can also be manually changed
outfile='out'

client_id = args[0]
client_secret = args[1]
username = args[2]
api_key = args[3]

#check if zip file exists
if not os.path.isfile(zip_file_path):
    raise Exception('Zip file not found in path')

veryfi_client = Client(client_id, client_secret, username, api_key)
response = veryfi_client.process_document(zip_file_path)

# get api text responce and split by document
docs=response['ocr_text'].split('\x0c')

counter=0
for i in docs:
    t=i.split('\n')
    t=[j.split('\t') for j in t]
    docs[counter]=t
    counter+=1

#sup1: Kw1 in invoice
#sup2: name in caps and without numbers

# find the location of a key-word (approximate) in a document
# takes a string keyword, nested list of strings and an integer
# returns an integer tuple of internal and external ositions
def findKwLoc(kw,doc,sensibility=3):
    pi=0
    for i in doc:

        pj=0
        for j in i:
            dst=textdistance.damerau_levenshtein.distance(kw,j)
            
            if dst<sensibility:
                location=(pi,pj)
                return(location)
            pj+=1
        pi+=1
    

#detect if a string has numbers on it
#takes a string and returns a boolean
def has_numbers(inputString):
    return bool(re.search(r'\d', inputString))

#detect if a string has lowercase letters on it
#takes a string and returns a boolean
def has_lowercase(inputString):
    return bool(re.search(r'[a-z]', inputString))


kw1='BILLING INSTRUCTIONS MAL YOUR INVOICES IN DUPLICATE TO CONSIGNEE'

# Looks for the vendor name using a subset of the document given by the keywords position
# -1 will be used if the kw is not found

vendor_names=[]
for i in docs:
    poss=findKwLoc(kw1,i,3)
    if poss==None:
        vendor_names.append(-1)
        continue
    options=[j[0] for j in i[0:poss[0]]]
    boli=[not (has_numbers(j) or has_lowercase(j) or j=='') for j in options]
    options=list(np.array(options)[boli])
    vendor_names.append(' '.join(options))
    
    
    

#Keywords used for limiting search of shipping and billing details

kw2='AS SHOWN BELOW'
kw3='SHIPMENT TO ARRIVE NOT LATER THAN'

#sup3: Kw2 in invoice
#sup4: Kw3 in invoice
#sup5: "TO:" not in shipping details 
#sup6: shipping details has more than 3 lines

# subset the document using the keywords
shippinngDeets=[]
for i in docs:
    poss1=findKwLoc(kw2,i,3)
    poss2=findKwLoc(kw3,i,3)
    if poss1==None or poss2==None:
        shippinngDeets.append(-1)
        continue
    poss1=list(poss1)
    poss2=list(poss2)
    if poss1==None or poss2==None:
        shippinngDeets.append(-1)
        continue
    poss1[0]=poss1[0]+2
    poss2[0]=poss2[0]-1
    
    shippinngDeets.append(i[poss1[0]:poss2[0]])

# use TO: to further delimit the search
for i in range(len(shippinngDeets)):
    if type(shippinngDeets[i])!=list:
        continue
    frst3=shippinngDeets[i][0:3]
    frst3=[' '.join(j) for j in frst3]
    counter=0
    index=-1
    for j in frst3:
        if 'TO:' in j:
            index=counter
        counter+=1
    if index==-1:
        continue
    [shippinngDeets[i].pop(0) for k in range(index+1)]

#sup7: Shipping details are not included if kw 'ATTACH' is included in the description

kw4='ATTACH'


# determine if 'ATTACH' is present document, 
# returns boolean
def isattached(doc):
    for i in doc:
        for j in i:
            if kw4 in j.upper():
                return(True)
    return(False)

#sup 8: shipping details has at least one line

#Divide billing and shipping details in separate lists,
#Takes a subset of a document as a nested list of strings
#returns list comprised of two lists of strings and a boolean 
#indicating if 'ATTACH' was found

def breakShipping(doc):
    attached=isattached(doc)
    counter=0
    bills=[]
    ships=[]
    for i in doc:
        if sum([len(j) for j in i])<2:
            continue
        
        if '' in i:
            bill=i[0:i.index('')]
            ship=i[i.index(''):]
        elif counter!=0 and not attached:
            if len(i)%2==0:
                bill=i[0:int(len(i)/2)]
                ship=i[int(len(i)/2):]
            else:
                bill=i[0:int((len(i)-1)/2)]
                ship=i[int((len(i)+1)/2):]
        elif counter==0 and attached:
            ship=i[-1]
            bill=i[0:-1]
        else:
            ship=['']
            bill=i
        ships.append(ship)
        bills.append(bill)
        counter+=1
    return([bills,ships,attached])

#Takes a subset of a document as a nested list of strings
#Returns a tupple with billing_name, billing_address, 
#shipping_name, shipping_adress as strings or -1 if not found

def giveshipping(doc):
    breaked=breakShipping(doc)
    billname=' '.join(breaked[0][0])
    billname=billname.replace('  ',' ')
    billadd=list(chain(*breaked[0][1:]))
    billadd=' '.join(billadd)
    billadd=billadd.replace('  ',' ')
    if breaked[2]:
        shipname='ATTACHED'
        shipadd='ATTACHED'
    else:
        shipname=' '.join(breaked[1][0])
        shipname=shipname.replace('  ',' ')
        shipadd=list(chain(*breaked[1][1:]))
        shipadd=' '.join(shipadd)
        shipadd=shipadd.replace('  ',' ')
    return(billname, billadd, shipname, shipadd)

#organizes shipping and billing details in variables

bill_to_names=[]
bill_to_address=[]
ship_to_names=[]
ship_to_address=[]

for i in shippinngDeets:
    if i!=-1:
        proc=giveshipping(i)
        bill_to_names.append(proc[0])
        bill_to_address.append(proc[1])
        ship_to_names.append(proc[2])
        ship_to_address.append(proc[3])
    else:
        bill_to_names.append(-1)
        bill_to_address.append(-1)
        ship_to_names.append(-1)
        ship_to_address.append(-1)

#replaces consecutive spaces in a string with
# a single space
def undobbleSpace(x):
    y=x
    while '  ' in y:
        y=y.replace('  ',' ')
    return(y)

# find the location of a key-word (approximate) in a document
# takes a string keyword, list of strings and an integer
# returns an integer with the location of the keyword
def findKwCon(kw,doc,sensibility=3):
    counter=0
    for i in doc:
        dst=textdistance.damerau_levenshtein.distance(kw,i)
        if dst<sensibility:
            return(counter)
        counter+=1
    
#subsets a string if it has more than 3 spaces, returns
# the sring unaltered otherwise
def beforeThirdSpace(x):
    spaces=[i.start() for i in re.finditer(r" ",x)]
    if len(spaces)>=3:
        return(x[0:spaces[2]])
    else:
        return(x)

#kws for delimiting the position of the items information
kw5='QUANTITY CODE NO. DESCRIPTION PRICE'
kw6='ACCOUNTING CHARGE NO.'

# extracts line items from a nested list sting document
# returns a tuple of strings with the items name, price and
# description; or -1 if not found
# We assume only one item is pressent 

def startitem(doc):
    # unnest the document
    connected=[undobbleSpace(' '.join(i[0:])) for i in doc]
    # subset the document
    pi=findKwCon(kw5,connected,3)
    if type(pi)!=int:
        return(-1,-1,-1)
    pi+=1
    connected=[beforeThirdSpace(i) for i in connected]
    pf=findKwCon(kw6,connected,3)
    # return -1's if subset was unsuccessfull
    if type(pf)!=int:
        return(-1,-1,-1)
    pf-=1
    connected=doc[pi:pf]
    count1=0
    found=False
    # find number and remove it from the document
    for i in connected:
        if found:
            break
        count2=0
        for j in i:
            if j.replace(',','').replace('.','').isnumeric():
                found=True
                break
            count2+=1
        count1+=1
    if found:
        number=connected[count1-1][count2]
        del connected[count1-1][count2]
    else:
        number=-1
    # find the price and remove it from the document
    found=False
    count1=0
    for i in connected:
        if found:
            break
        count2=0
        for j in i:
            if '$' in j:
                found=True
                break
            count2+=1
        count1+=1
    if found:
        price=connected[count1-1][count2]
        del connected[count1-1][count2]
    else:
        price=-1
    # return the rest of the document as description
    desc=[' '.join(i) for i in connected]
    desc=undobbleSpace(' '.join(desc))
    return([number,price,desc])

line_items=[startitem(i) for i in docs]

# Get the file names to use them as names for the json output files
zip = zipfile.ZipFile(zip_file_path)
file_name_list=zip.namelist()
boli=[i[0]!='_' for i in file_name_list]
file_name_list=list(np.array(file_name_list)[boli])

#make output file if it doesent exist
if not os.path.isdir(outfile):
    os.mkdir(outfile)

# Write output in json format, skips it if there are more -1's
# than the tolerance parameter; the original filename if presenved
# and text after the last . is changed for 'json'; '.json' is added
# if no . is found

tolerance=4
for i in range(len(file_name_list)):
    dicti={'vendor_name':vendor_names[i],'bill_to_name':bill_to_names[i],
           'bill_to_address':bill_to_address[i],'ship_to_name':ship_to_names[i],
           'ship_to_address':ship_to_address[i],
           'line_items':{'quantity':line_items[i][0],'description':line_items[i][1],
                        'price':line_items[i][2]}}
    cadena=list(dicti.values())
    cadena=cadena[0:5]+list(cadena[5].values())
    boli=sum([j==-1 for j in cadena])
    if boli>tolerance:
        warnings.warn('Warning:file format of file '+file_name_list[i]+' was not recognized and skipped')
        continue
    if not '.' in file_name_list[i]:
        filename=file_name_list[i]+'.json'
    else:
        filename=file_name_list[i][0:file_name_list[i].rfind('.')-1]+'.json'
    with(open(os.path.join(outfile,filename),'w') as file):
        json.dump(dicti,file)
    
    if len(file_name_list)!=len(vendor_names):
        warnings.warning('Warning: one or more of your files contains more than one page, please correct.')