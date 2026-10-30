package com.attribution.user.config;

import java.util.concurrent.Executor;
import java.util.concurrent.ThreadPoolExecutor;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

/**
 * 自选池采集任务线程池配置。
 *
 * <p>线程池由 Spring 创建与管理，随应用生命周期关闭，
 * 不在 Service 中直接 {@code Executors.new*}（见 docs/规范文档/纵向分层规范/Service层规范.md §3.7）。
 */
@Configuration
public class PoolTaskExecutorConfig {

    @Bean("poolTaskExecutor")
    public Executor poolTaskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(4);
        executor.setMaxPoolSize(8);
        executor.setQueueCapacity(64);
        executor.setThreadNamePrefix("pool-collect-");
        // 队列满时由调用线程执行，保证任务不丢失
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(30);
        executor.initialize();
        return executor;
    }
}
