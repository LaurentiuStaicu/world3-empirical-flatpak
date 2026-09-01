.PHONY: validate test science-test promotion reproduce fetch-science-inputs integrity-manifest science-input-manifest flatpak

validate:
	python3 scripts/validate.py

test:
	python3 -m unittest discover -s tests -v

science-test: reproduce
	uv run --project science --extra world3-03 python scripts/generate_science_test_artifacts.py
	uv run --project science --extra world3-03 python -m unittest discover -s science/tests -v

promotion:
	python3 scripts/promotion_gate.py

reproduce:
	uv run --project science --extra world3-03 python scripts/reproduce_scientific_results.py

fetch-science-inputs:
	python3 scripts/fetch_science_inputs.py

integrity-manifest:
	python3 scripts/generate_integrity_manifest.py

science-input-manifest:
	python3 scripts/generate_science_input_manifest.py

flatpak: validate test
	./build-flatpak.sh
