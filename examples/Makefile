all: adder

TOOL=../pp.py

ex1: pp.ex1
	$(TOOL) $< -p context.json -k val=10 name=miguel -v -o $@

ex2: pp.ex2
	$(TOOL) $< -p context.json -k val=10 name=miguel -v -o $@

ex3: pp.ex3
	$(TOOL) $< -p context.json -k val=10 name=miguel -v -o $@

adder.v: pp.adder.v
	$(TOOL) $< -p context.json -k WIDTH=10 -v -o $@

clean:
	$(RM) adder.v ex1 ex2 ex3 *.debug.py
