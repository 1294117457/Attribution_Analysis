package com.attribution.domain.repository;

import com.attribution.domain.entity.MktCalendarEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

@Repository
public interface MktCalendarRepository extends JpaRepository<MktCalendarEntity, Long> {

    Optional<MktCalendarEntity> findByExchangeAndCalDate(String exchange, LocalDate calDate);

    List<MktCalendarEntity> findByExchangeAndCalDateBetweenOrderByCalDateAsc(
        String exchange, LocalDate start, LocalDate end);

    @Query("SELECT MAX(c.calDate) FROM MktCalendarEntity c "
        + "WHERE c.exchange = :exchange AND c.isOpen = true AND c.calDate <= :asOf")
    LocalDate findLastOpenDate(@Param("exchange") String exchange, @Param("asOf") LocalDate asOf);
}
