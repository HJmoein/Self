#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <fstream>
#include <sstream>
#include <thread>
#include <chrono>
#include <iomanip>
#include <ctime>
#include <td/telegram/td_json_client.h>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

const int32_t API_ID = 29834234;
const std::string API_HASH = "552c01d21d127def060f2915aedeebf9";
const std::string TARGET_USERNAME = "Moein_917";

struct ChatPaginationState {
    int64_t oldest_message_id = 0;
    bool is_completed = false;
    std::string chat_name = "Unknown";
    std::vector<std::string> accumulated_messages;
};

class CleanTelegramExporter {
private:
    void* client;
    bool is_logged_in = false;
    int64_t target_chat_id = 0;
    bool target_resolved = false;
    bool chats_listed = false;

    std::map<int64_t, ChatPaginationState> chat_states;

    std::string escape_html(const std::string& str) {
        std::string result;
        for (char c : str) {
            switch (c) {
                case '&':  result += "&amp;"; break;
                case '\"': result += "&quot;"; break;
                case '\'': result += "&#39;"; break;
                case '<':  result += "&lt;"; break;
                case '>':  result += "&gt;"; break;
                default:   result += c; break;
            }
        }
        return result;
    }

    std::string format_timestamp(int64_t unix_time) {
        if (unix_time <= 0) return "";
        std::time_t t = static_cast<std::time_t>(unix_time);
        std::tm* tm_info = std::localtime(&t);
        char buffer[80];
        std::strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", tm_info);
        return std::string(buffer);
    }

public:
    CleanTelegramExporter() {
        client = td_json_client_create();
    }

    ~CleanTelegramExporter() {
        td_json_client_destroy(client);
    }

    void send_request(const json& request) {
        std::string req_str = request.dump();
        td_json_client_send(client, req_str.c_str());
    }

    json receive_response(double timeout = 1.0) {
        const char* res = td_json_client_receive(client, timeout);
        if (res) {
            try {
                return json::parse(res);
            } catch (...) {
                return nullptr;
            }
        }
        return nullptr;
    }

    void init() {
        send_request({
            {"@type", "setLogVerbosityLevel"},
            {"new_verbosity_level", 0}
        });

        json set_params = {
            {"@type", "setTdlibParameters"},
            {"parameters", {
                {"database_directory", "tdlib_secure_db"},
                {"use_message_database", true},
                {"use_secret_chats", false},
                {"api_id", API_ID},
                {"api_hash", API_HASH},
                {"system_language_code", "en"},
                {"device_model", "Server Exporter"},
                {"application_version", "3.4"}
            }}
        };
        send_request(set_params);
    }

    std::string build_html_document(int64_t chat_id, const std::string& chat_name, const std::vector<std::string>& messages) {
        std::stringstream html;
        html << "<!DOCTYPE html>\n<html lang=\"fa\" dir=\"rtl\">\n<head>\n"
             << "<meta charset=\"UTF-8\">\n<title>Private Chat Archive - " << chat_name << "</title>\n"
             << "<style>\n"
             << "body { font-family: Tahoma, sans-serif; background-color: #0f172a; color: #e2e8f0; margin: 0; padding: 20px; direction: rtl; }\n"
             << ".container { max-width: 750px; margin: 0 auto; }\n"
             << ".chat-header { background-color: #1e293b; padding: 15px 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #334155; }\n"
             << ".chat-header h2 { margin: 0 0 5px 0; color: #38bdf8; font-size: 18px; }\n"
             << ".chat-header p { margin: 0; color: #94a3b8; font-size: 12px; }\n"
             << ".msg-card { background-color: #1e293b; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px; border-right: 4px solid #3b82f6; }\n"
             << ".msg-card.me { border-right-color: #10b981; background-color: #162438; }\n"
             << ".meta { font-size: 11px; color: #64748b; margin-bottom: 6px; display: flex; justify-content: space-between; }\n"
             << ".text { white-space: pre-wrap; word-wrap: break-word; line-height: 1.6; font-size: 14px; }\n"
             << "</style>\n</head>\n<body>\n<div class=\"container\">\n"
             << "<div class=\"chat-header\">\n<h2>" << escape_html(chat_name) << "</h2>\n"
             << "<p>Chat ID: " << chat_id << " | Private Chat Archive</p>\n</div>\n";

        for (const auto& msg : messages) {
            html << msg << "\n";
        }

        html << "</div>\n</body>\n</html>";
        return html.str();
    }

    void run() {
        init();
        while (true) {
            json response = receive_response(2.0);
            if (response.is_null()) continue;

            std::string type = response.value("@type", "");

            if (type == "error") {
                continue;
            }

            if (type == "updateAuthorizationState") {
                std::string state = response["authorization_state"]["@type"];
                if (state == "authorizationStateWaitPhoneNumber") {
                    std::cout << "Please enter phone number: ";
                    std::string phone;
                    std::cin >> phone;
                    send_request({{"@type", "setAuthenticationPhoneNumber"}, {"phone_number", phone}});
                } else if (state == "authorizationStateWaitCode") {
                    std::cout << "Please enter code: ";
                    std::string code;
                    std::cin >> code;
                    send_request({{"@type", "checkAuthenticationCode"}, {"code", code}});
                } else if (state == "authorizationStateWaitPassword") {
                    std::cout << "Please enter 2FA password: ";
                    std::string password;
                    std::cin >> password;
                    send_request({{"@type", "checkAuthenticationPassword"}, {"password", password}});
                } else if (state == "authorizationStateReady") {
                    std::cout << "Logged in successfully. Starting operation..." << std::endl;
                    is_logged_in = true;
                    send_request({{"@type", "searchPublicChat"}, {"username", TARGET_USERNAME}});
                }
            }

            if (type == "chat" && !target_resolved) {
                if (response.contains("id")) {
                    target_chat_id = response["id"];
                    target_resolved = true;
                    send_request({{"@type", "getChats"}, {"chat_list", {{"@type", "chatListMain"}}}, {"limit", 100}});
                }
            }

            if (type == "chats" && !chats_listed) {
                if (response.contains("chat_ids")) {
                    auto chat_ids = response["chat_ids"];
                    for (auto& chat_id_json : chat_ids) {
                        int64_t cid = chat_id_json.get<int64_t>();
                        send_request({
                            {"@type", "getChat"},
                            {"chat_id", cid}
                        });
                    }
                    chats_listed = true;
                }
            }

            if (type == "chat" && target_resolved) {
                int64_t cid = response.value("id", 0);
                
                if (cid != 0 && cid != target_chat_id && response.contains("type")) {
                    std::string chat_type = response["type"].value("@type", "");
                    
                    if (chat_type == "chatTypePrivate") {
                        std::string chat_title = response.value("title", "Private Chat");
                        
                        if (chat_states.find(cid) == chat_states.end()) {
                            chat_states[cid] = ChatPaginationState();
                            chat_states[cid].chat_name = chat_title;

                            send_request({
                                {"@type", "getChatHistory"},
                                {"chat_id", cid},
                                {"from_message_id", 0},
                                {"offset", 0},
                                {"limit", 100},
                                {"only_local", false}
                            });
                        }
                    }
                }
            }

            if (type == "messages") {
                if (response.contains("messages") && response.contains("total_count")) {
                    int total = response["total_count"];
                    auto msgs = response["messages"];

                    if (total > 0 && msgs.is_array() && !msgs.empty()) {
                        int64_t current_chat_id = 0;
                        int64_t oldest_id_in_batch = 0;

                        for (auto& msg : msgs) {
                            if (msg.contains("chat_id")) {
                                current_chat_id = msg["chat_id"];
                            }
                            if (msg.contains("id")) {
                                oldest_id_in_batch = msg["id"];
                            }

                            if (current_chat_id != 0 && chat_states.find(current_chat_id) != chat_states.end()) {
                                int64_t msg_id = msg.value("id", 0);
                                int64_t date_val = msg.value("date", 0);
                                bool is_out = msg.value("is_out", false);
                                std::string time_str = format_timestamp(date_val);

                                std::string text_content = "";
                                if (msg.contains("content") && msg["content"].contains("text")) {
                                    text_content = msg["content"]["text"].value("text", "");
                                } else {
                                    text_content = "[Media / Non-text message]";
                                }

                                std::string card_class = is_out ? "msg-card me" : "msg-card";
                                std::string sender_label = is_out ? "You" : "Contact";

                                std::stringstream msg_html;
                                msg_html << "<div class=\"" << card_class << "\">\n"
                                         << "<div class=\"meta\"><span>" << sender_label << " (#" << msg_id << ")</span><span>" << time_str << "</span></div>\n"
                                         << "<div class=\"text\">" << escape_html(text_content) << "</div>\n"
                                         << "</div>";

                                chat_states[current_chat_id].accumulated_messages.push_back(msg_html.str());
                            }
                        }

                        if (current_chat_id != 0 && oldest_id_in_batch > 0 && msgs.size() >= 50) {
                            chat_states[current_chat_id].oldest_message_id = oldest_id_in_batch;

                            send_request({
                                {"@type", "getChatHistory"},
                                {"chat_id", current_chat_id},
                                {"from_message_id", oldest_id_in_batch},
                                {"offset", 0},
                                {"limit", 100},
                                {"only_local", false}
                            });
                        } else if (current_chat_id != 0) {
                            auto& state = chat_states[current_chat_id];
                            if (!state.is_completed && !state.accumulated_messages.empty()) {
                                state.is_completed = true;

                                std::string final_html = build_html_document(current_chat_id, state.chat_name, state.accumulated_messages);

                                auto now = std::chrono::system_clock::now();
                                auto now_sec = std::chrono::system_clock::to_time_t(now);
                                std::string filename = "PrivateArchive_" + std::to_string(current_chat_id) + "_" + std::to_string(now_sec) + ".html";

                                std::ofstream outfile(filename);
                                outfile << final_html;
                                outfile.close();

                                if (target_resolved && target_chat_id != 0) {
                                    send_request({
                                        {"@type", "sendMessage"},
                                        {"chat_id", target_chat_id},
                                        {"input_message_content", {
                                            {"@type", "inputMessageDocument"},
                                            {"document", {{"@type", "inputFileLocal"}, {"path", filename}}},
                                            {"caption", {{"@type", "formattedText"}, {"text", "Private Chat Archive: " + filename}}}
                                        }}
                                    });
                                    std::this_thread::sleep_for(std::chrono::seconds(1));
                                }
                            }
                        }
                    }
                }
            }
        }
    }
};

int main() {
    CleanTelegramExporter exporter;
    exporter.run();
    return 0;
}
