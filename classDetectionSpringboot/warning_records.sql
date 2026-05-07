CREATE TABLE IF NOT EXISTS `warning_records` (
  `id` int NOT NULL AUTO_INCREMENT,
  `video_source` varchar(500) DEFAULT NULL,
  `detection_type` varchar(50) DEFAULT NULL,
  `risk_level` varchar(20) DEFAULT NULL,
  `behavior_type` varchar(50) DEFAULT NULL,
  `duration_seconds` double DEFAULT NULL,
  `trigger_time` varchar(50) DEFAULT NULL,
  `reason` varchar(500) DEFAULT NULL,
  `advice` text,
  `status` varchar(50) DEFAULT '未处理',
  `username` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
