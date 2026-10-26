.PHONY: build watch clean

build:
	jekyll build

watch:
	jekyll build --watch

clean:
	jekyll clean
