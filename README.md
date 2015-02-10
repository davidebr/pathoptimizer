# pathoptimizer

A pathcv/soma optimizer. 

For long time I had an horrible script in bash to optimize Path Collective Variables (PCVs) and I had an all-mighty but equally horrible script for optimization for String-method with Optimal Molecular Alignment.
Now my intent is to create a simpler and limited version of a python script that could robustly perform the optimization for both PCVs and SOMA (since they are procedurally similar) in plumed2. This might give a chance for someone else to take over and use these tecniques I have been using with some success and happiness through the years. For the time being one severe limitation is that the CVs will be cartesian coordinates with optimal molecular alignment. Hopefully at a certain point,  this limitation will be relieved. 
