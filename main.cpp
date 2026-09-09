#include <iostream>
#include <string>
#include <vector>
#include <memory>
#include <sstream>
#include <td/telegram/td_json_client.h>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

// تنظیمات حساب و مقصد
const int32_t API_ID = 29834234;
const std::string API_HASH = "552c01d21d127def060f2915aedeebf9";
const std::string TARGET_USER = "Moein_917";

class TelegramExporter {
private:
    void* client;

public:
    TelegramExporter() {
        client = td_json_client_create();
    }

    ~TelegramExporter() {
        td_json_client_destroy(client);
    }

    // ارسال درخواست به TDLib
    void send_request(const json& request) {
        std::string req_str = request.dump();
        td_json_client_send(client, req_str.c_str());
    }

    // دریافت پاسخ از TDLib
    json receive_response(double timeout = 1.0) {
        const char* res = td_json_client_receive(client, timeout);
        if (res) {
            return json::parse(res);
        }
        return nullptr;
    }

    // راه‌اندازی اولیه و احراز هویت
    void init() {
        // بستن لاگ‌های اضافه و اضافی TDLib برای خلوت شدن ترمینال
        send_request({
            {"@type", "setLogVerbosityLevel"},
            {"new_verbosity_level", 1}
        });

        json set_params = {
            {"@type", "setTdlibParameters"},
            {"parameters", {
                {"database_directory", "tdlib"},
                {"use_message_database", true},
                {"use_secret_chats", false},
                {"api_id", API_ID},
                {"api_hash", API_HASH},
                {"system_language_code", "en"},
                {"device_model", "Desktop C++"},
                {"application_version", "1.0"}
            }}
        };
        send_request(set_params);
    }

    // ساخت فایل HTML از پیام‌ها
    std::string generate_html(const std::string& chat_name, const std::vector<json>& messages) {
        std::stringstream html;
        html << "<!DOCTYPE html><html lang='fa' dir='rtl'><head><meta charset='UTF-8'>"
             << "<style>body{font-family:Tahoma;background:#0f172a;color:#e2e8f0;padding:20px;}"
             << ".msg{background:#1e293b;padding:10px;margin:10px 0;border-radius:8px;}</style></head><body>"
             << "<h2>Chat with: " << chat_name << "</h2>";

        for (const auto& msg : messages) {
            if (msg.contains("content") && msg["content"].contains("text")) {
                std::string text = msg["content"]["text"]["text"];
                html << "<div class='msg'>" << text << "</div>";
            }
        }

        html << "</body></html>";
        return html.str();
    }

    // متد اصلی اجرا
    void run() {
        init();
        std::cout << "[+] TDLib Client started successfully." << std::endl;

        // حلقه اصلی جهت پردازش رویدادها و دریافت لیست چت‌ها
        while (true) {
            json response = receive_response(2.0);
            if (response.is_null()) continue;

            std::string type = response.value("@type", "");

            // چک کردن وضعیت لاگین
            if (type == "updateAuthorizationState") {
                std::string state = response["authorization_state"]["@type"];
                if (state == "authorizationStateWaitPhoneNumber") {
                    std::cout << "Please enter phone number: ";
                    std::string phone;
                    std::cin >> phone;
                    send_request({
                        {"@type", "setAuthenticationPhoneNumber"},
                        {"phone_number", phone}
                    });
                } else if (state == "authorizationStateWaitCode") {
                    std::cout << "Please enter auth code: ";
                    std::string code;
                    std::cin >> code;
                    send_request({
                        {"@type", "checkAuthenticationCode"},
                        {"code", code}
                    });
                } else if (state == "authorizationStateReady") {
                    std::cout << "[+] Logged in! Fetching chats..." << std::endl;
                    send_request({{"@type", "getChats"}, {"limit", 100}});
                }
            }

            // پردازش لیست چت‌ها
            if (type == "chats") {
                auto chat_ids = response["chat_ids"];
                for (auto& chat_id : chat_ids) {
                    send_request({
                        {"@type", "getChatHistory"},
                        {"chat_id", chat_id},
                        {"from_message_id", 0},
                        {"offset", 0},
                        {"limit", 100},
                        {"only_local", false}
                    });
                }
            }
        }
    }
};

int main() {
    TelegramExporter exporter;
    exporter.run();
    return 0;
}
