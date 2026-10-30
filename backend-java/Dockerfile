# backend-java: single fat jar (attribution-app) with all modules
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build
COPY pom.xml .
COPY attribution-common/pom.xml attribution-common/pom.xml
COPY attribution-collector-client/pom.xml attribution-collector-client/pom.xml
COPY attribution-market/pom.xml attribution-market/pom.xml
COPY attribution-concept/pom.xml attribution-concept/pom.xml
COPY attribution-user/pom.xml attribution-user/pom.xml
COPY attribution-auth/pom.xml attribution-auth/pom.xml
COPY attribution-app/pom.xml attribution-app/pom.xml
RUN mvn -q dependency:go-offline -pl attribution-app -am
COPY attribution-common/src attribution-common/src
COPY attribution-collector-client/src attribution-collector-client/src
COPY attribution-market/src attribution-market/src
COPY attribution-concept/src attribution-concept/src
COPY attribution-user/src attribution-user/src
COPY attribution-auth/src attribution-auth/src
COPY attribution-app/src attribution-app/src
RUN mvn -q -DskipTests -pl attribution-app -am package

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /build/attribution-app/target/attribution-app-*.jar app.jar
ENV SERVER_PORT=8080
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
