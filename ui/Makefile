all: main.py settings.py

clean:
	rm -f *.py

%.py: %.ui
	pyuic6 -x $< -o $@
