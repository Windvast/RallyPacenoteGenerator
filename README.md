# RallyPacenoteGenerator

A rally pacenote generator based on AMap WebAPI.

## Introduction
As you may already know, rally drivers use an unique way to describe competitive stages, which are actually open roads taht we can drive everyday.
The idea is to create a tool that can automatically generate some pacenotes according to GIS info rather than we do it manually, here data from AMap have been introduced.

## Getting Started
0. Of course you are familiar with rally and pacenote system
1. Fork or clone this repo
2. Get a free api on https://lbs.amap.com/ 
3. Start to play with it!

## Where to improve
1. Calculate the change of raidus of a u-turn corner.
2. Merge adjacent straight sections or corners.
3. Generator natural pacenotes, e.g., "right 3 *into* left 4 when the distance inbetween is short, "right 3 *and* left 4 when the distance inbetween is moderate (er, how to define moderate or short?)
4. Visualization.
5. Try to add infomation about altitude, so we can have "dip" "jump" "crest".

## Author
**windvast**

Your can find me on https://space.bilibili.com/1649008 (user name: windvast), or just write to me: windvast@gmail.com.
