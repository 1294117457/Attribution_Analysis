package com.attribution.domain.service;

import com.attribution.domain.entity.FinReportEntity;
import org.springframework.stereotype.Service;

/**
 * 盈利能力派生指标域服务。
 *
 * <p>封装所有「跨 entity、纯计算、无副作用」的盈利能力指标，例如：
 * <ul>
 *   <li>归母净利率（profit_margin %）</li>
 *   <li>（后续可扩展：毛利率、ROE、净利同比等）</li>
 * </ul>
 *
 * <h2>设计原则</h2>
 * <ul>
 *   <li>本服务 <b>不知道</b> HTTP、不返回前端字段、不访问 Repository。</li>
 *   <li>Entity（{@link FinReportEntity}）只保留原始字段与基本 getter，
 *       业务派生指标一律由本服务计算并返回 {@link Double}（无法计算返回 {@code null}，绝不返回 0）。</li>
 *   <li>应用层（{@code application.service} / {@code infrastructure.query}）负责
 *       拉取最新一期报表并把结果填到 VO。</li>
 * </ul>
 *
 * @see <a href="https://en.wikipedia.org/wiki/Net_margin">Net profit margin</a>
 */
@Service
public class ProfitabilityDomainService {

    /** 收入为零或绝对值过小时的容差，避免除零 */
    private static final double REVENUE_EPSILON = 1e-9;

    /**
     * 归母净利率（俗称「净利润率%」）。
     *
     * <p>公式：{@code n_income_attr_p / revenue × 100}。
     *
     * <p>A 股业内惯例（Tushare / Wind / 同花顺），用于衡量公司把收入转化为归母净利润的效率。
     * 注意区分：
     * <ul>
     *   <li>{@code net margin}（净利率）= {@code n_income / revenue}（净利润总数）</li>
     *   <li>{@code gross margin}（毛利率）= 需要成本字段，<b>本服务暂不实现</b></li>
     * </ul>
     *
     * @param report 财报快照（建议使用「最新一期」年报/季报）
     * @return 净利润率 %；无法计算（字段缺失或收入为 0）返回 {@code null}
     */
    public Double computeProfitMarginPct(FinReportEntity report) {
        if (report == null) {
            return null;
        }
        Double revenue = firstNonNull(report.getRevenue(), report.getTotalRevenue());
        return computeProfitMarginPct(report.getNIncomeAttrP(), revenue);
    }

    /**
     * 直接接收数字的版本（便于单测 / 复用）。
     *
     * @param nIncomeAttrP 归母净利润
     * @param revenue      营业总收入（{@code revenue} 优先；缺则用 {@code total_revenue}）
     * @return 净利润率 %；参数缺失或收入接近 0 返回 {@code null}
     */
    public Double computeProfitMarginPct(Double nIncomeAttrP, Double revenue) {
        if (nIncomeAttrP == null || revenue == null) {
            return null;
        }
        if (Math.abs(revenue) < REVENUE_EPSILON) {
            return null;
        }
        return nIncomeAttrP / revenue * 100.0;
    }

    private static <T> T firstNonNull(T a, T b) {
        return a != null ? a : b;
    }
}
