As proof of concept, *documents_to_processT.zip* was used as input, with its output in the *out* folder, this file includes unrelated PDF files (in order to evaluate exclusion) and a new invoice taken from the kaggle repo, which has the same format as the original files but was not used to write the package's code.

ests are performed with *Test_1.py* including one unit test and one integration test; test outputs are stored in in *test.log* an executed using `pytest` on the script `Test_1.py` on the main folder, as this scripts makes an API call, you will need to enter your credentials at line 22 of *Test_1.py*

