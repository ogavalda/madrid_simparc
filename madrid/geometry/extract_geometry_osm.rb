# frozen_string_literal: true

# Runs *only* the BuildResidentialHPXML measure (the same vendored measure used
# by the real batch) against a saved argument set, and saves the resulting
# OpenStudio model. This captures the geometry envelope (walls/roof/floor/
# windows/doors) as a connected, architecturally coherent 3D box, BEFORE
# HPXMLtoOpenStudio's explode_surfaces() spreads walls apart for shading-safe
# EnergyPlus simulation (explode_surfaces only runs in the HPXMLtoOpenStudio
# measure, never in BuildResidentialHPXML, so this model is never exploded).
#
# Usage:
#   openstudio madrid/geometry/extract_geometry_osm.rb <args.json> <output.osm>

require 'openstudio'
require 'json'
require_relative '../../measures/HPXMLtoOpenStudio/resources/meta_measure'

args_json_path = ARGV[0]
output_osm_path = ARGV[1]

args = JSON.parse(File.read(args_json_path))

model = OpenStudio::Model::Model.new
runner = OpenStudio::Measure::OSRunner.new(OpenStudio::WorkflowJSON.new)
measures_dir = File.join(File.dirname(__FILE__), '..', '..', 'measures')
measures = { 'BuildResidentialHPXML' => [args] }

success = apply_measures(measures_dir, measures, runner, model, false)
puts "BuildResidentialHPXML success: #{success}"
unless success
  runner.result.stepErrors.each { |e| puts "ERROR: #{e}" }
end
runner.result.stepWarnings.each { |w| puts "WARNING: #{w}" }

model.save(output_osm_path, true)
puts "Saved connected geometry model: #{output_osm_path} (#{model.getSurfaces.size} surfaces, #{model.getSubSurfaces.size} sub-surfaces, #{model.getSpaces.size} spaces)"
