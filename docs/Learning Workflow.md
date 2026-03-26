
- Take my notes for each class
	- After finishing my notes for the class, I want the following things from my assistant
		- Anki Flashcards based on the lectures to be created
			- should be automatically added, I do not want to manually add them
				- should be added to the same classes flashcard deck
				- should be one of the following format types:
					- cloze deletion
						- this is a must have question
					- image occlusion
						- if these cannot be created create a list of flashcards to be created with clear directions and a image link already found
							- example: image: Glycolysis: image_link, cover each the enzymes, coenzymes, energy carriers, etc...
					- multiple choice questions
			- **Problems that could occur here**
				- anki may not support agents directly adding to flashcards
					- could look into potentially contributing to the anki repository in response, worst case scenario I run a beta build myself.
		- Short Answer based review questions
			- **Requriement**
				- these should be titled similarly to the note it is based on and added to the folder of the course/class titled 'Review Questions'
		- A summary/ extension of my notes
			- should flush out concepts which I may have touched on but did not extensively cover
			- should be added to the page(s) that are new in my notes
			- **Requirement**
				- the summaries should be generated on a page by page basis
		- Answers to the questions I left in my notes
			- **Note**
				- I will need to establish a consistent way of denoting messages
					- ex: all blocks prefixed with ??? and ended with ??? are questions
					- multi line version ?\*\*?
			- Should be added to the page where the question was
	- After receiving the short answer questions I will produce a response, that could be handwritten or typed into 
		- If a picture is taken it will be converted to a response and added to the corresponding review questions page
			- **Requirements**
				- should have the option to use a local ML model to perform the conversion in case sensitive information is written.
	- After the review questions are completely modified my assistant should review my responses, and provide feedback based on them
		- the feedback should be added to the corresponding review questions page
	- At the end of each day my assistant should review the ankki flashcards I reviewed that day, and provide me with a morning review over the concepts I was weak in from the previous day


Tools I would like to use to accomplish this
- Obsidian (note taking app)
- Anki
- Some agent based framework like Openclaw
	- **Requirements**
		- cannot be based on Java script 
		- Cannot be produced by a recent creator
		- cannot be solely developed by a chinese developer

		