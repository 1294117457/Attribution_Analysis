package com.attribution.domain.vo;

import jakarta.persistence.Column;
import jakarta.persistence.Embeddable;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Objects;

@Embeddable
public class TradeDate {

    @Column(name = "trade_date", nullable = false)
    private LocalDate date;

    public TradeDate() {
    }

    public TradeDate(LocalDate date) {
        this.date = Objects.requireNonNull(date, "TradeDate cannot be null");
    }

    public TradeDate(String dateStr) {
        Objects.requireNonNull(dateStr, "TradeDate cannot be null");
        this.date = LocalDate.parse(dateStr, DateTimeFormatter.ISO_DATE);
    }

    public LocalDate getDate() {
        return date;
    }

    public void setDate(LocalDate date) {
        this.date = date;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof TradeDate other)) return false;
        return Objects.equals(date, other.date);
    }

    @Override
    public int hashCode() {
        return Objects.hash(date);
    }

    @Override
    public String toString() {
        return date != null ? date.toString() : "null";
    }
}
