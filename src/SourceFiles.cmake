set(SOURCEFILES
    # Source Files
    ${CMAKE_CURRENT_LIST_DIR}/main.cpp
    ${CMAKE_CURRENT_LIST_DIR}/mainFrame.cpp
    ${CMAKE_CURRENT_LIST_DIR}/logger/logger.cpp
    ${CMAKE_CURRENT_LIST_DIR}/config/config.cpp
    ${CMAKE_CURRENT_LIST_DIR}/baseComPanel/baseComPanel.cpp
    ${CMAKE_CURRENT_LIST_DIR}/subscriber/subscriberPanel.cpp
    ${CMAKE_CURRENT_LIST_DIR}/subscriber/subscriber.cpp
    ${CMAKE_CURRENT_LIST_DIR}/subscriber/topicFrame.cpp
    ${CMAKE_CURRENT_LIST_DIR}/requester/requesterPanel.cpp
    ${CMAKE_CURRENT_LIST_DIR}/requester/requester.cpp
    ${CMAKE_CURRENT_LIST_DIR}/publisher/publisherPanel.cpp
    ${CMAKE_CURRENT_LIST_DIR}/publisher/publisher.cpp
    ${CMAKE_CURRENT_LIST_DIR}/replyer/replyerPanel.cpp
    ${CMAKE_CURRENT_LIST_DIR}/replyer/replyer.cpp
)

set(INCLUDEDIRS
    ${CMAKE_SOURCE_DIR}/src/
    ${CMAKE_SOURCE_DIR}/src/logger/
    ${CMAKE_SOURCE_DIR}/src/common/
    ${CMAKE_SOURCE_DIR}/src/config/
)
