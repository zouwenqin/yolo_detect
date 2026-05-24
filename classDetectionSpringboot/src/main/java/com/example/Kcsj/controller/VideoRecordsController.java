package com.example.Kcsj.controller;

import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.Kcsj.common.Result;
import com.example.Kcsj.entity.VideoRecords;
import com.example.Kcsj.mapper.VideoRecordsMapper;
import org.springframework.web.bind.annotation.*;

import javax.annotation.Resource;
import java.io.File;
import java.net.URL;
import java.net.URLDecoder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;

@RestController
@RequestMapping("/videoRecords")
public class VideoRecordsController {
    @Resource
    VideoRecordsMapper videoRecordsMapper;

    @GetMapping("/all")
    public Result<?> GetAll() {
        return Result.success(videoRecordsMapper.selectList(null));
    }
    @GetMapping("/{id}")
    public Result<?> getById(@PathVariable int id) {
        System.out.println(id);
        return Result.success(videoRecordsMapper.selectById(id));
    }

    @GetMapping
    public Result<?> findPage(@RequestParam(defaultValue = "1") Integer pageNum,
                              @RequestParam(defaultValue = "10") Integer pageSize,
                              @RequestParam(defaultValue = "") String search,
                              @RequestParam(defaultValue = "") String search1,
                              @RequestParam(defaultValue = "") String search3,
                              @RequestParam(defaultValue = "") String search2) {
        LambdaQueryWrapper<VideoRecords> wrapper = Wrappers.<VideoRecords>lambdaQuery();
        wrapper.orderByDesc(VideoRecords::getStartTime);
        if (StrUtil.isNotBlank(search)) {
            wrapper.like(VideoRecords::getUsername, search);
        }
        if (StrUtil.isNotBlank(search1)) {
            wrapper.like(VideoRecords::getKind, search1);
        }
        if (StrUtil.isNotBlank(search2)) {
            wrapper.like(VideoRecords::getWeight, search2);
        }
        if (StrUtil.isNotBlank(search3)) {
            wrapper.like(VideoRecords::getConf, search3);
        }
        Page<VideoRecords> Page = videoRecordsMapper.selectPage(new Page<>(pageNum, pageSize), wrapper);
        return Result.success(Page);
    }

    @DeleteMapping("/{id:\\d+}")
    public Result<?> delete(@PathVariable int id) {
        VideoRecords record = videoRecordsMapper.selectById(id);
        if (record != null) {
            deleteResultVideo(record.getOutVideo());
        }
        videoRecordsMapper.deleteById(id);
        return Result.success();
    }

    @DeleteMapping("/byInput")
    public Result<?> deleteByInputVideo(@RequestParam(defaultValue = "") String inputVideo) {
        if (StrUtil.isBlank(inputVideo)) {
            return Result.error("-1", "missing inputVideo");
        }
        LambdaQueryWrapper<VideoRecords> wrapper = Wrappers.<VideoRecords>lambdaQuery()
                .eq(VideoRecords::getInputVideo, inputVideo);
        List<VideoRecords> records = videoRecordsMapper.selectList(wrapper);
        for (VideoRecords record : records) {
            deleteResultVideo(record.getOutVideo());
            videoRecordsMapper.deleteById(record.getId());
        }
        return Result.success(records.size());
    }

    private void deleteResultVideo(String outVideo) {
        if (StrUtil.isBlank(outVideo)) {
            return;
        }
        try {
            String fileName = extractFileName(outVideo);
            if (StrUtil.isBlank(fileName)) {
                return;
            }
            Path filesDir = Paths.get(System.getProperty("user.dir"), "files").toAbsolutePath().normalize();
            Path target = filesDir.resolve(fileName).normalize();
            if (target.startsWith(filesDir)) {
                Files.deleteIfExists(target);
            }
        } catch (Exception ignored) {
            // Keep record deletion tolerant when the derived result video is already missing.
        }
    }

    private String extractFileName(String outVideo) throws Exception {
        String path = outVideo;
        if (outVideo.startsWith("http://") || outVideo.startsWith("https://")) {
            path = new URL(outVideo).getPath();
        }
        String fileName = new File(path).getName();
        return URLDecoder.decode(fileName, "UTF-8");
    }

    @PostMapping("/update")
    public Result<?> updates(@RequestBody VideoRecords videoRecords) {
        videoRecordsMapper.updateById(videoRecords);
        return Result.success();
    }


    @PostMapping
    public Result<?> save(@RequestBody VideoRecords videoRecords) {
        System.out.println(videoRecords);
        videoRecordsMapper.insert(videoRecords);
        return Result.success();
    }
}
