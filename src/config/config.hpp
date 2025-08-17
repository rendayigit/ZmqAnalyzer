#pragma once

#include "common.hpp"

#include <nlohmann/json.hpp>
#include <vector>

const std::string CONFIG_FILE_PATH = getExecutableDirectory() + "config.json";
constexpr int MAX_LIST_SIZE = 25;

class Config {
public:
  static void updateKeyInConfig(const std::string &key, const std::string &value);
  static void addValueToListInConfig(const std::string &key, const std::string &value);
  static void removeValueFromListInConfig(const std::string &key, const std::string &value);
  static std::vector<std::string> getListItemsFromConfig(const std::string &key);

private:
  Config() = default;
};