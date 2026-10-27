.PHONY: build watch clean check-jekyll install-ruby install-jekyll

build: check-jekyll
	jekyll build

watch: check-jekyll
	jekyll build --watch

clean: check-jekyll
	jekyll clean

check-jekyll:
	@if ! command -v jekyll >/dev/null 2>&1; then \
		echo "Jekyll is required. Run 'make install-jekyll' to install it."; \
		exit 1; \
	fi

install-ruby:
	@if ! command -v brew >/dev/null 2>&1; then \
		echo "Homebrew is required. Install it by following the instructions at https://brew.sh/"; \
		exit 1; \
	fi
	brew install -y ruby@4.0

install-jekyll: install-ruby
	PATH="$$(brew --prefix ruby@4.0)/bin:$$PATH" gem install jekyll
	@echo "Add $$(brew --prefix ruby@4.0)/bin and $$(brew --prefix)/lib/ruby/gems/4.0.0/bin to your PATH to use Jekyll."
