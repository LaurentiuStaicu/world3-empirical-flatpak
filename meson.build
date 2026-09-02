project(
  'io.github.laurentiustaicu.World3Empirical',
  'vala',
  'c',
  version: '0.10.2',
  meson_version: '>=0.59.0',
  default_options: ['warning_level=2']
)

gnome = import('gnome')

gtk = dependency('gtk4')
granite = dependency('granite-7')
cc = meson.get_compiler('c')
math = cc.find_library('m', required: true)

version_config = configuration_data()
version_config.set('PROJECT_VERSION', meson.project_version())
build_config = configure_file(
  input: 'src/BuildConfig.vala.in',
  output: 'BuildConfig.vala',
  configuration: version_config
)

executable(
  meson.project_name(),
  'src/Application.vala',
  'src/MainWindow.vala',
  'src/ScenarioData.vala',
  'src/ChartView.vala',
  build_config,
  dependencies: [gtk, granite, math],
  install: true
)

install_data(
  'data/io.github.laurentiustaicu.World3Empirical.desktop',
  install_dir: get_option('datadir') / 'applications'
)

install_data(
  'data/io.github.laurentiustaicu.World3Empirical.metainfo.xml',
  install_dir: get_option('datadir') / 'metainfo'
)

install_data(
  'data/icons/io.github.laurentiustaicu.World3Empirical.svg',
  install_dir: get_option('datadir') / 'icons' / 'hicolor' / 'scalable' / 'apps'
)

install_data(
  'data/scenarios/population.csv',
  'data/scenarios/industry_per_capita.csv',
  'data/scenarios/food_per_capita.csv',
  'data/scenarios/pollution_pressure.csv',
  'data/scenarios/human_welfare.csv',
  'data/scenarios/industry_total.csv',
  'data/scenarios/persistent_pollution_stock.csv',
  'data/scenarios/resources_remaining_pct.csv',
  'data/scenarios/backtest_2019_latest.csv',
  'data/scenarios/backtest_multi_origin.csv',
  'data/scenarios/fit_diagnostics.csv',
  'data/scenarios/parameter_identifiability.csv',
  'data/scenarios/candidate_ranking.csv',
  'data/scenarios/validation_candidate_ranking.csv',
  'data/scenarios/bridge_validation.csv',
  'data/scenarios/lookup_extrapolation_audit.csv',
  'data/scenarios/bau_hybrid_2026_manifest.json',
  'data/scenarios/scenario_schema.json',
  'data/scenarios/release_integrity.json',
  install_dir: get_option('datadir') / meson.project_name() / 'scenarios'
)
