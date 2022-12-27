
all:
	make -C examples all

clean:
	make -C examples clean
	$(RM) -r __pycache__ __pycache__/.mypy_cache
	$(RM) -r .mypy_cache tests/.mypy_cache
