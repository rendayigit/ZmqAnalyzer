#pragma once

// #include <climits>
#include <filesystem>

#include <linux/limits.h>
#include <string>
#include <unistd.h>

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

