# Offline bridge for Zucchini's direct nlohmann_json dependency and the
# nested Cucumber Messages CPM declaration. The exact CPM module and every
# source tree remain caller-pinned by the external artifact manifest.
if(NOT DEFINED MIW_CPM_MODULE OR NOT EXISTS "${MIW_CPM_MODULE}")
    message(FATAL_ERROR "MIW_CPM_MODULE must name the pinned CPM.cmake file")
endif()

include("${MIW_CPM_MODULE}")
CPMRegisterPackage(nlohmann_json 3.12.0)
