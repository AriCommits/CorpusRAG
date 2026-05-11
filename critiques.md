# Introduction 
This document will serve as a notebook ofor trying the cli cocmmands and testing to esnure they work as expected / correctly.

# Corpus CLI


think it might be a good idea to consolidate flaschards, quizzes underneath a learning cli path. 

it also might be a good idea to consolidate haandwriting, summaries, video,  rag, and learning into a tools cli command.

this waya users go 
corpus tools
whatever tool they needd. 

and the learning tools can be modularized/ made distinct



## Collections
- Info: this command wworks from the tui but does not work from the cli
- merge: does not work and should be removed
    - needs to eb removed from the tui access to managmenet as well
- Rename: does not exist and shoul dbe remoed
    - needed to be remove from the tui as well
- tui
    - quitting leaves the tui unusable 
corpus r- consider addign an update path command here for each collection



## db
- list works as expected but displays http request taking up space in the terminal (not very asthetic)
- backup-all: should not exits, should be an extensions of backup with all as a flag. also backing up failed with error: object of type ndarray is not json serializable indicating issue with copying vector embeddings
    - also displays http requests
- export: does not throw error but behavior i snot correct
    - looks like this functionality is the same as backup maybe the two should be consolidated as 'copy' command
    - although the command works, the vector embedding itself is not given, also the model used to generate the emebedding should probably be stored in the metadata so the entire export will be self contained and the information encoded can be useful in other settings.
    - also http requessts displayed in cli
    - ermbeddings should be included by default
    - again outputing embeddings from ndarray returned unserializable error from json 



## rag
- doctor tool should be moved up to base cli entry point corpus doctor
- sync: should store the path used to ingest documents from so the user can just specify the collection name instead of have having to also give the path. the path can be useful as a syncing arguement though becasue if the path the changes the user needs to have a way to specify the new path.
- ui: should not require collections argument, it should be optional.   
    - Also users need a wayu to select collctions from within the ui
    - consider changing the terminal bindings off of F1-5 because theya re still used for most systems. fo rinstance if someone is using corpus rag from the integated terminal in a ide they may be unable to use the hotkeys.
    - after exiting here the terminal still works. Maybe add a collections management system here so in addition to acces from the `corpus collections ui ` entrypoint the collections can be managed from the rag entrypoint

    
    






