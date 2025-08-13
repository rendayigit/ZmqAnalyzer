#pragma once

#include "logger.hpp"

#include <climits>
#include <filesystem>
#include <fstream>
#include <linux/limits.h>
#include <nlohmann/json.hpp>
#include <string>
#include <unistd.h>
#include <vector>

static std::string getExecutableDirectory() {
  char execPathStr[PATH_MAX]; // NOLINT(hicpp-avoid-c-arrays, modernize-avoid-c-arrays,
                              // cppcoreguidelines-avoid-c-arrays)

  // Get the path of the executable
  ssize_t len = readlink("/proc/self/exe", execPathStr, PATH_MAX - 1);
  if (len != -1) {
    execPathStr[len] = '\0'; // NOLINT(cppcoreguidelines-pro-bounds-constant-array-index)
  }

  // Get the path of the executable's parent directory
  std::filesystem::path execPath(execPathStr);
  std::filesystem::path parentPath = execPath.parent_path();

  // Navigate to the project's bin directory
  std::string pathStr = parentPath.string();

  // Find the last directory in the path (e.g., "/bin" etc.)
  std::string dirName = parentPath.filename().string();
  size_t dirPos = pathStr.rfind("/" + dirName);

  if (dirPos != std::string::npos) {
    // Keep everything up to and including the directory name
    pathStr = pathStr.substr(0, dirPos + 1 + dirName.length());
  }

  return (pathStr + '/');
}

const std::string CONFIG_FILE_PATH = getExecutableDirectory() + "config.json";
constexpr int MAX_LIST_SIZE = 25;

static void updateKeyInConfig(const std::string &key, const std::string &value) {
  nlohmann::json config;
  std::ifstream configFile(CONFIG_FILE_PATH);

  if (configFile.is_open()) {
    try {
      // Read the existing config
      configFile >> config;
      configFile.close();

      // Update the key
      config[key] = value;

      // Write the updated config back to the file
      std::ofstream outConfigFile(CONFIG_FILE_PATH, std::ios::trunc);

      if (outConfigFile.is_open()) {
        outConfigFile << config.dump(2);
        outConfigFile.close();
      } else {
        Logger::warn("Could not open config file for writing: " + CONFIG_FILE_PATH);
      }
    } catch (const std::exception &e) {
      Logger::warn("Error writing to config file: " + std::string(e.what()));
    }
  } else {
    Logger::warn("Could not open config file for reading: " + CONFIG_FILE_PATH);
  }
}

static void addValueToListInConfig(const std::string &key, const std::string &value) {
  nlohmann::json config;
  std::ifstream configFile(CONFIG_FILE_PATH);

  if (configFile.is_open()) {
    try {
      // Read the existing config
      configFile >> config;
      configFile.close();

      // Add the value to list
      config[key].push_back(value);

      // Limit the number of items stored
      if (config[key].size() > MAX_LIST_SIZE) {
        config[key].erase(config[key].begin());
      }

      // Write the updated config back to the file
      std::ofstream outConfigFile(CONFIG_FILE_PATH, std::ios::trunc);

      if (outConfigFile.is_open()) {
        outConfigFile << config.dump(2);
        outConfigFile.close();
      } else {
        Logger::warn("Could not open config file for writing: " + CONFIG_FILE_PATH);
      }
    } catch (const std::exception &e) {
      Logger::warn("Error writing to config file: " + std::string(e.what()));
    }
  } else {
    Logger::warn("Could not open config file for reading: " + CONFIG_FILE_PATH);
  }
}

static std::vector<std::string> getListItemsFromConfig(const std::string &key) {
  nlohmann::json config;
  std::ifstream configFile(CONFIG_FILE_PATH);
  std::vector<std::string> items;

  if (configFile.is_open()) {
    try {
      configFile >> config;
      configFile.close();

      if (config.contains(key) and config[key].is_array()) {

        for (const auto &item : config[key]) {
          items.push_back(item.get<std::string>());
        }
      }
    } catch (const std::exception &e) {
      Logger::warn("Error reading list from config: " + std::string(e.what()));
    }
  } else {
    Logger::warn("Could not open config file for reading: " + CONFIG_FILE_PATH);
  }

  return items;
}