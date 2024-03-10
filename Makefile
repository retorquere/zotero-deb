repo: rebuild-apt
	./rebuild-apt

%: %.cr
	crystal build --no-debug --release -o $@ $<
