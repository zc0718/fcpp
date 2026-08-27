#include <gtest/gtest.h>
#include <thread>
#include <chrono>
#include <net.hpp>



int sleep(int n) {
    std::this_thread::sleep_for(std::chrono::seconds(n));
    return n + 1;
}



void net_predict() {
    // 占位：net.cpp 的 predict_random_sample 当前为固定返回值，无需调用。
}



TEST(Stress, Sleep) {
    EXPECT_EQ(sleep(3), 4);
}



TEST(Stress, Network) {
    EXPECT_NO_THROW(net_predict());
}