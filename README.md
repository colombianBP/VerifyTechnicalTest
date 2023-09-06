# VerifyTechnicalTest
Data acquisition specialist technical test, by Nicolas Hoyos Bertin; data originally aquired from https://www.kaggle.com/datasets/holtskinner/invoices-document-ai

A solution was implemented automatically extract certain data from an image or pdf document; directed specifically at the ones present inside *documents_to_process.zip*. The produced solution is presented as a python package *veryfiProcess* to use you must install the requirements, and load the package; first declare an object of the *credentials* class with your ORC API credentials as strings ordered as `client_id, client_secret, username, api_key` and then run the class function *write_output* with the path of your desired input file and output folder as parameters, the defaults are : ‘documents_to_process.zip’ and ‘out’. This will access the API and process your documents producing a Json file for each, containing the desired output as described per requirements.

Input specifications:

A zip file is expected, if PDF documents are used, they can only contain one page. This project intends only to extract data from files with the same format as the invoices present in documents_to_process.zip documents in other formats will be simply skipped, producing a warning and no output.

Sample outputs are provided in *out*; testing is available at the *test* folder; and additionally, a commented notebook *processing.ipynb* with the same processing as the package is provided for ease of revision.

A mixed approach was used; with flexible identification of keywords available as part of the format (assumed to be static), and regex based identification of specific data; a more in-depth explanation of each step is provided as comments along both the notebook and package executable.  
