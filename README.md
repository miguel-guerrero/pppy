# PPPY (Pre Processing in Python)

Utility/pre-processor to generate text programmatically.


## 1. Embedding a block of python code

    <%
    code line 1
    code line 2
    %>

indentation is important and must match the expected one based on the previous
code

if you need to generate a verbatim piece of output use emit:

    <%
    for i in range(5):
       emit(f"---- {i} ----")
    %>



## 2. Interpolating a python variable or an expression

For example 

    3*8 = ${3*8}

will print

    3*8 = 24

or

    <%
    x=1
    y=2
    %>

    x + y = ${x+y}

will print

    x + y = 3



## 3. Embedding a line of python

    % (with a space after) is used to insert python code

use 'end' instead of unindent when needed to resolve indentation ambiguity

    % if x > 0:
    aaa
    %   if y < 0:
    %      x += 1
    bbb  

Is bbb covered by the 2nd if?  it is a bit ambiguous as the prints implicit
in the non-python lines has no indentation. By default they are assumed to 
belong to the innermost block opened in python, but to resolve this you may 
need to insert explicit end's

    % if x > 0:
    aaa
    %   if y < 0:
    %      x += 1
    %   end
    bbb  

OR (this is equivalent to the default)

    % if x > 0:
    aaa
    %   if y < 0:
    %      x += 1
    bbb  
    %   end

