from veryfiProcess import mypackage as vr
import pickle as pk
import numpy as np
import os
import sys
import time


with open('test/processedDocs.pkl','rb') as file:
    fake=pk.load(file)
    

def test_give_vendor_names():
    kw1='BILLING INSTRUCTIONS MAL YOUR INVOICES IN DUPLICATE TO CONSIGNEE'
    result=vr.give_vendor_names(fake,kw1)
    expected=['THE AMERICAN TOBACCO COMPANY']*4
    assert result==expected
    

def test_output():
    ### Please enter your credentials here
    creds=['','','',''] #client_id, client_secret, username, api_key
    ### Please enter your credentials here
    creds=vr.credentials(creds[0],creds[1],creds[2],creds[3])
    creds.write_output('test/documents_to_processT.zip','test/out')
    time.sleep(1)
    result=list(os.listdir('test/out'))
    result=list(np.array(result)[['.json' in i for i in result]])[0]
    assert '006007694.json' == result
    

