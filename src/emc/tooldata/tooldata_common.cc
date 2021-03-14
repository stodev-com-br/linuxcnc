/*
** This file is part of a refactor of internal  tool data management
** and incorporates work from removed files:
**     src/emc/ini/initool.cc
**     src/emc/rs274ngc/tool_parse.cc
**
** Copyright: 2021
** Author:    Dewey Garrett <dgarrett@panix.com>
**
** This program is free software; you can redistribute it and/or modify
** it under the terms of the GNU General Public License as published by
** the Free Software Foundation; either version 2 of the License, or
** (at your option) any later version.
**
** This program is distributed in the hope that it will be useful,
** but WITHOUT ANY WARRANTY; without even the implied warranty of
** MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
** GNU General Public License for more details.
**
** You should have received a copy of the GNU General Public License
** along with this program; if not, write to the Free Software
** Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
*/
#include <stdio.h>
#include <string.h>
#include <rtapi_string.h>
#include "tooldata.hh"

#define UNEXPECTED_MSG fprintf(stderr,"UNEXPECTED %s %d\n",__FILE__,__LINE__);

static bool     is_random_toolchanger = 0;
static int      nonrandom_idx = 0; // 'fakepocket' counter
static bool     add_init_initialized = 0;
static tooldb_t db_mode = DB_NOTUSED;

void tooldata_init(bool random_toolchanger)
{
    is_random_toolchanger = random_toolchanger;
} // tooldata_init

struct CANON_TOOL_TABLE tooldata_entry_init()
{
    struct CANON_TOOL_TABLE tdata;
    tdata.toolno      = -1;
    tdata.pocketno    =  0;
    tdata.diameter    =  0;
    tdata.frontangle  =  0;
    tdata.backangle   =  0;
    tdata.orientation =  0;
    ZERO_EMC_POSE(tdata.offset);

    return tdata;
} // tooldata_entry_init()

void tooldata_set_db(tooldb_t mode)
{
    db_mode = mode;
    return;
} //tooldata_set_db()

void tooldata_add_init(int nonrandom_start_idx)
{
    // initialize file-static vars need for tooldata_add_line()
    nonrandom_idx        = nonrandom_start_idx;
    add_init_initialized = 1;
    return;
} // tooldata_add_init()

int tooldata_read_entry(const char *input_line,
                        char *ttcomments[])
{
    char work_line[CANON_TOOL_ENTRY_LEN];
    const char *token;
    char *buff, *comment;
    int toolno,orientation,valid=1;
    EmcPose offset; //tlo
    double diameter, frontangle, backangle;
    int idx = 0;
    int realpocket = 0;

    if (!add_init_initialized) {
        fprintf(stderr,"!!! PROBLEM no init %s\n",__FILE__);
        return -1;
    }
    strcpy(work_line, input_line);

    CANON_TOOL_TABLE empty = tooldata_entry_init();
    toolno      = empty.toolno;
    diameter    = empty.diameter;
    frontangle  = empty.frontangle;
    backangle   = empty.backangle;
    orientation = empty.orientation;
    offset      = empty.offset;

    buff = strtok(work_line, ";");
    if (strlen(buff) <=1) {
        //fprintf(stderr,"skip blankline %s\n",__FILE__);
        return 0;
    }
    comment = strtok(NULL, "\n");

    token = strtok(buff, " ");
    while (token != NULL) {
        switch (toupper(token[0])) {
        case 'T':
            if (sscanf(&token[1], "%d", &toolno) != 1)
                valid = 0;
            break;
        case 'P':
            if (sscanf(&token[1], "%d", &idx) != 1) {
                valid = 0;
                break;
            }
            realpocket = idx;  //random toolchanger
            if (!is_random_toolchanger) {
                if (   (nonrandom_idx <= 0)
                    || (nonrandom_idx >= CANON_POCKETS_MAX) ) {
                    printf("Out-of-range nonrandom_idx=%d. Skipping tool=%d\n",
                           nonrandom_idx,toolno);
                    valid = 0;
                    break;
                }
                idx = nonrandom_idx; // nonrandom toolchanger
                (nonrandom_idx)++;
            }
            if (idx < 0 || idx >= CANON_POCKETS_MAX) {
                printf("max pocket number is %d. skipping tool %d\n",
                       CANON_POCKETS_MAX - 1, toolno);
                valid = 0;
                break;
            }
            break;
        case 'D':
            if (sscanf(&token[1], "%lf", &diameter) != 1)
                valid = 0;
            break;
        case 'X':
            if (sscanf(&token[1], "%lf", &offset.tran.x) != 1)
                valid = 0;
            break;
        case 'Y':
            if (sscanf(&token[1], "%lf", &offset.tran.y) != 1)
                valid = 0;
            break;
        case 'Z':
            if (sscanf(&token[1], "%lf", &offset.tran.z) != 1)
                valid = 0;
            break;
        case 'A':
            if (sscanf(&token[1], "%lf", &offset.a) != 1)
                valid = 0;
            break;
        case 'B':
            if (sscanf(&token[1], "%lf", &offset.b) != 1)
                valid = 0;
            break;
        case 'C':
            if (sscanf(&token[1], "%lf", &offset.c) != 1)
                valid = 0;
            break;
        case 'U':
            if (sscanf(&token[1], "%lf", &offset.u) != 1)
                valid = 0;
            break;
        case 'V':
            if (sscanf(&token[1], "%lf", &offset.v) != 1)
                valid = 0;
            break;
        case 'W':
            if (sscanf(&token[1], "%lf", &offset.w) != 1)
                valid = 0;
            break;
        case 'I':
            if (sscanf(&token[1], "%lf", &frontangle) != 1)
                valid = 0;
            break;
        case 'J':
            if (sscanf(&token[1], "%lf", &backangle) != 1)
                valid = 0;
            break;
        case 'Q':
            if (sscanf(&token[1], "%d", &orientation) != 1)
                valid = 0;
            break;
        default:
            if (strncmp(token, "\n", 1) != 0)
                valid = 0;
            break;
        }
        token = strtok(NULL, " ");
    } // while token

    if (valid) {
        CANON_TOOL_TABLE tdata = tooldata_entry_init();
        tdata.toolno      = toolno;
        tdata.pocketno    = realpocket;
        tdata.offset      = offset;
        tdata.diameter    = diameter;
        tdata.frontangle  = frontangle;
        tdata.backangle   = backangle;
        tdata.orientation = orientation;
        if (tooldata_put(tdata,idx) == IDX_FAIL) {
            UNEXPECTED_MSG;
        }
        if (ttcomments && comment) {
             strcpy(ttcomments[idx], comment);
        }
    } else {
         return -1;
    }
    return idx;
} // tooldata_read_entry()

void tooldata_format_toolline (int idx,
                               CANON_TOOL_TABLE tdata,
                               char * ttcomments[],
                               char formatted_line[CANON_TOOL_ENTRY_LEN]
                               )
{
    char tmp[CANON_TOOL_ENTRY_LEN-1] = {0};
    snprintf(tmp,sizeof(tmp),"T%-3d P%-3d"
            ,tdata.toolno
            ,is_random_toolchanger ? idx : tdata.pocketno);
    strncat(formatted_line,tmp,CANON_TOOL_ENTRY_LEN-1);
#define ITEM(item,fmt) if (tdata.item) { \
                          snprintf(tmp,sizeof(tmp),fmt,tdata.item); \
                          strncat(formatted_line,tmp,CANON_TOOL_ENTRY_LEN-1); \
                       }
    ITEM(diameter,       " D%+f");
    ITEM(offset.tran.x,  " X%+f");
    ITEM(offset.tran.y,  " Y%+f");
    ITEM(offset.tran.z,  " Z%+f");
    ITEM(offset.a,       " A%+f");
    ITEM(offset.b,       " B%+f");
    ITEM(offset.c,       " C%+f");
    ITEM(offset.u,       " U%+f");
    ITEM(offset.v,       " V%+f");
    ITEM(offset.w,       " W%+f");
    ITEM(frontangle,     " I%+f");
    ITEM(backangle,      " J%+f");
    ITEM(orientation,    " Q%d" );
#undef ITEM
    if (ttcomments) {  //ignore if nil pointer
       snprintf(tmp,sizeof(tmp)," ;%s\n",ttcomments[idx]);
       strncat(formatted_line,tmp,CANON_TOOL_ENTRY_LEN-1);
    }
    return;
} // tooldata_format_toolline()

int tooldata_load(const char *filename,
                  char *ttcomments[])
{
    FILE *fp;
    char input_line[CANON_TOOL_ENTRY_LEN];
    char orig_line[CANON_TOOL_ENTRY_LEN];

    if (db_mode == DB_ACTIVE) { //expect data loaded from db
         if (tooldata_db_getall()) {
            fprintf(stderr,
              "\ntooldata_load: Failed to load tooldata from database\n\n");
            db_mode = DB_NOTUSED;
            return -1;
         }
         return 0;
    }

    if(!filename) return -1;

    // clear out tool table
    // (Set vars to indicate no tool in pocket):
    int  idx;
    for (idx = 0; idx < CANON_POCKETS_MAX; idx++) {
        if(ttcomments) ttcomments[idx][0] = '\0';
    }
    tooldata_reset();

    // open tool table file
    if (NULL == (fp = fopen(filename, "r"))) {
        // can't open file
        return -1;
    }

    // after initializing all available pockets,
    // subsequent read from filename will update the last_index
    // which becomes available by tooldata_last_index_get()
    tooldata_last_index_set(0); // (only mmap uses)

    const int nonrandom_start_idx = 1; // when reading file start at 0
    tooldata_add_init(nonrandom_start_idx);

    while (!feof(fp)) {
        // for nonrandom machines, just read the tools into pockets 1..n
        // no matter their tool numbers.  NB leave the spindle pocket 0
        // unchanged/empty.
        if (NULL == fgets(input_line, CANON_TOOL_ENTRY_LEN, fp)) {
            break;
        }
        strcpy(orig_line, input_line);

        // parse and store one line from tool table file
        int entry_idx = tooldata_read_entry(input_line, ttcomments);
        if (entry_idx <0) {
            printf("File: %s Unrecognized line skipped:\n    %s",filename, orig_line);
            continue;
        }

        if (!is_random_toolchanger) {
            CANON_TOOL_TABLE spindletool;
            if (tooldata_get(&spindletool,0) != IDX_OK) {
                continue;
            }
            CANON_TOOL_TABLE edata;  // just added
            if (tooldata_get(&edata,entry_idx) != IDX_OK) {
                UNEXPECTED_MSG;
            }
            if (!is_random_toolchanger && spindletool.toolno == edata.toolno) {
                spindletool = edata;
                tooldata_put(spindletool,0);
            }
        }
    } // while

    // close the file
    fclose(fp);

    return 0;
} // tooldata_load()

static void write_tool_line(FILE* fp,int idx,char *ttcomments[])
{
    CANON_TOOL_TABLE tdata;
    if (tooldata_get(&tdata,idx) != IDX_OK) {return;}
    if (db_mode == DB_ACTIVE && idx != 0 ) {
        return;
    }

    if (tdata.toolno != -1) {
        char theline[CANON_TOOL_ENTRY_LEN] = {0};
        tooldata_format_toolline (idx,tdata,ttcomments,theline);
        fprintf(fp,"%s",theline);
    }
    return;
} // write_tool_line()

int tooldata_save(const char *filename,
                  char *ttcomments[CANON_POCKETS_MAX])
{
    int idx;
    FILE *fp;
    int start_idx;

    if (db_mode == DB_ACTIVE) {
        if (!is_random_toolchanger) {return 0;}
        filename = DB_SPINDLE_SAVE; //one entry tbl (nonran only)
    } else {
        if (filename[0] == 0) {
            UNEXPECTED_MSG;
        }
    }

    // open tool table file
    if (NULL == (fp = fopen(filename, "w"))) {
        // can't open file
        return -1;
    }

    if (db_mode == DB_ACTIVE) {
        int spindle_idx = 0;
        write_tool_line(fp,spindle_idx,ttcomments);
    } else {
        start_idx = is_random_toolchanger ? 0 : 1;
        for (idx = start_idx; idx < CANON_POCKETS_MAX; idx++) {
            write_tool_line(fp,idx,ttcomments);
        }
    }
    fclose(fp);
    return 0;
} //tooldata_save()
