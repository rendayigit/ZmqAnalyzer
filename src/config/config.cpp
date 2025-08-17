#include "config.hpp"

#include "logger.hpp"

#include <fstream>

void Config::updateKeyInConfig(const std::string &key, const std::string &value) {
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

void Config::addValueToListInConfig(const std::string &key, const std::string &value) {
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

void Config::removeValueFromListInConfig(const std::string &key, const std::string &value) {
  nlohmann::json config;
  std::ifstream configFile(CONFIG_FILE_PATH);

  if (configFile.is_open()) {
    try {
      // Read the existing config
      configFile >> config;
      configFile.close();

      // Remove the value from list
      auto &list = config[key];
      list.erase(std::remove(list.begin(), list.end(), value), list.end());

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

std::vector<std::string> Config::getListItemsFromConfig(const std::string &key) {
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
