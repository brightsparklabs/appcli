# BSL Application CLI Backup `file_filter`settings block

The `file_filter` block in the `stack-settings.yml` file allows for include and exclude lists to be used when creating a backup. [Glob](https://en.wikipedia.org/wiki/Glob_(programming)) pattern matching is used to determine what files should be included or excluded from the `data` and `conf` directories. Recursive glob patterns are enabled with the `**` notation.
Folder matches are ignored, only file matches will be placed in the backup and any necessary folders to maintain the hierarchy.

## YML key definitions

### file_filter

| key          | Description                                                                     |
| ------------ | ------------------------------------------------------------------------------- |
| data_dir     | Include and exclude glob lists for the `data` directory.                        |
| conf_dir     | Include and exclude glob lists for the `conf` directory.                        |

### data_dir / conf_dir
| key          | Description                                                                                                                        |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| include_list | A list of globs used to match files that will be include in the backup. If left blank or not present all files will be included.   |
| exclude_list | A list of globs used to match files that will be excluded from the backup. If left blank or not present no files will be excluded. |


    # filename: stack-settings.yml

    backups:
        -name: "a_name"
        file_filter:
            data_dir:
                include_list:
                    -
                exclude_list:
                    -
            conf_dir:
                include_list:
                    -
                exclude_list:
                    -

## Include lists

An include list specifies what files should be included in the backup. By default this will always match all files, it does this by inserting `**/*` when there are no patterns or the key is not present.

    # filename: stack-settings.yml

    backups:
        -name: "a_name"
         file_filter:
            data_dir:
                include_list:
                    - "a glob"

## Exclude lists

An exclude list specifies what files should be excluded from the backup. By default this will not match any files, it does this by inserting an empty glob pattern when there are no patterns or the key is not present.

    # filename: stack-settings.yml

    backups:
        -name: "a_name"
         file_filter:
            data_dir:
                exclude_list:
                    - "a glob"


## Examples

### Backup everything

To create a backup that contains everything in the data and conf directories either a complete recursive pattern should be used (`**/*`) or the `file_filter` key can be left out.

    # filename: stack-settings.yml

    backups:
        -name: "full_backups"
         frequency: "* * *"



### Only backup the data directory

To backup the `data` directory but ignore the `conf` directory a recursive pattern that matches everything will need to be used in the exclude list `**/*`.

    # filename: stack-settings.yml

    backups:
        -name: "data_only"
         file_filter:
            conf_dir:
                exclude_list:
                    - "**/*"
         frequency

### Only backup `.log` files

To only backup data that ends with `.log` a recursive pattern looking for log files is needed `**/*.log`.

    # filename: stack-settings.yml

    backups:
        -name: "logs"
         file_filter:
            conf_dir:
                include_list:
                    - "**/*.log"
            data_dir:
                include_list:
                    - "**/*.log"
         frequency:


### Backup the data root directory not including sub-folders

To backup the root directory of `data` a non-recursive wildcard pattern will be needed `*` for the `include_list` on `data` and a fully recursive match `**/*` for `exclude_list` on `conf`

```
example directory:
    data/
        search/
        engine/
        proxy/
        file1.yml
        file2.yml
        logs.log

    conf/
        settings.yml
        stack-settings.yml
        .git/
```
    # filename: stack-settings.yml

    backups:
        -name: "data_root"
         file_filter:
            conf_dir:
                exclude_list:
                    - "**/*"
            data_dir:
                include_list:
                    - "*"
         frequency:


```
example match:
    file1.yml
    file2.yml
    logs.log
```

