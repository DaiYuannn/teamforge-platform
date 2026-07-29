<template>
  <div class="page-container file-list-page">
    <PageHeader title="文件管理" subtitle="项目文件、版本与共享归档">
      <template #meta>
        <span class="page-meta">
          {{ workspaceMode === 'files' ? `共 ${total} 个文件` : `回收站 ${recycledFiles.length} 项` }}
        </span>
      </template>
      <template #actions>
        <el-radio-group v-model="workspaceMode" size="small" @change="handleWorkspaceChange">
          <el-radio-button value="files">文件</el-radio-button>
          <el-radio-button v-if="canViewRecycle" value="trash">回收站</el-radio-button>
        </el-radio-group>
        <template v-if="workspaceMode === 'files'">
          <el-tooltip content="管理标签" placement="bottom">
            <el-button
              v-if="canManageSelectedProject"
              :icon="CollectionTag"
              aria-label="管理标签"
              @click="openTagManager"
            />
          </el-tooltip>
          <el-tooltip content="新建文件夹" placement="bottom">
            <el-button
              v-if="canManageSelectedProject"
              :icon="FolderAdd"
              aria-label="新建文件夹"
              @click="openFolderDialog()"
            >
              新建文件夹
            </el-button>
          </el-tooltip>
          <el-button
            v-if="canUpload"
            type="primary"
            :icon="Upload"
            @click="openUploadDialog"
          >
            {{ uploadActionLabel }}
          </el-button>
        </template>
      </template>
    </PageHeader>

    <template v-if="workspaceMode === 'files'">
      <section class="file-workspace">
        <div class="filter-toolbar">
          <el-form :inline="true" :model="queryParams" @submit.prevent="handleSearch">
            <el-form-item label="项目">
              <el-select
                v-model="queryParams.project"
                class="project-filter"
                placeholder="全部项目"
                clearable
                filterable
                @change="handleProjectChange"
              >
                <el-option v-for="project in projectOptions" :key="project.id" :label="project.name" :value="project.id" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="isMobile && queryParams.project" label="文件夹">
              <el-select
                v-model="queryParams.folder"
                class="folder-filter"
                placeholder="全部文件"
                clearable
                @change="handleSearch"
              >
                <el-option label="项目根目录" value="root" />
                <el-option v-for="folder in folders" :key="folder.id" :label="folder.path" :value="folder.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="标签">
              <el-select
                v-model="queryParams.tag"
                class="tag-filter"
                placeholder="全部标签"
                clearable
                @change="handleSearch"
              >
                <el-option v-for="tag in availableTags" :key="tag.id" :label="tag.name" :value="tag.id">
                  <span class="tag-option-dot" :style="{ backgroundColor: tag.color }"></span>
                  {{ tag.name }}
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="级别">
              <el-select
                v-model="queryParams.level"
                class="level-filter"
                placeholder="全部级别"
                clearable
                @change="handleSearch"
              >
                <el-option
                  v-for="(item, key) in FILE_LEVEL_MAP"
                  :key="key"
                  :label="item.label"
                  :value="key"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="关键词">
              <el-input
                v-model="queryParams.search"
                class="search-filter"
                placeholder="文件名"
                clearable
                @keyup.enter="handleSearch"
                @clear="handleSearch"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
              <el-button :icon="Refresh" @click="handleReset">重置</el-button>
            </el-form-item>
          </el-form>
        </div>

        <div class="workspace-body" :class="{ 'without-sidebar': !queryParams.project || isMobile }">
          <aside v-if="queryParams.project && !isMobile" class="folder-sidebar">
            <div class="folder-sidebar-heading">
              <strong>文件夹</strong>
              <el-tooltip v-if="canManageSelectedProject" content="新建文件夹" placement="top">
                <el-button text :icon="Plus" aria-label="新建文件夹" @click="openFolderDialog()" />
              </el-tooltip>
            </div>
            <button
              type="button"
              class="folder-root"
              :class="{ active: queryParams.folder === undefined }"
              @click="selectFolder(undefined)"
            >
              <el-icon><FolderOpened /></el-icon>
              <span>全部文件</span>
            </button>
            <button
              type="button"
              class="folder-root"
              :class="{ active: queryParams.folder === 'root' }"
              @click="selectFolder('root')"
            >
              <el-icon><Folder /></el-icon>
              <span>项目根目录</span>
            </button>
            <el-tree
              v-if="folderTree.length"
              :data="folderTree"
              node-key="id"
              default-expand-all
              :expand-on-click-node="false"
              :highlight-current="typeof queryParams.folder === 'number'"
              :current-node-key="typeof queryParams.folder === 'number' ? queryParams.folder : undefined"
              @node-click="handleFolderNodeClick"
            >
              <template #default="{ data }">
                <div class="folder-node">
                  <el-icon><Folder /></el-icon>
                  <span class="folder-node-name">{{ data.name }}</span>
                  <span class="folder-count">{{ data.file_count }}</span>
                  <div v-if="canManageSelectedProject" class="folder-node-actions" @click.stop>
                    <el-tooltip content="新建子文件夹" placement="top">
                      <el-button text :icon="Plus" aria-label="新建子文件夹" @click="openFolderDialog(undefined, data.id)" />
                    </el-tooltip>
                    <el-tooltip content="编辑文件夹" placement="top">
                      <el-button text :icon="Edit" aria-label="编辑文件夹" @click="openFolderDialog(data)" />
                    </el-tooltip>
                    <el-tooltip content="删除文件夹" placement="top">
                      <el-button text type="danger" :icon="Delete" aria-label="删除文件夹" @click="handleFolderDelete(data)" />
                    </el-tooltip>
                  </div>
                </div>
              </template>
            </el-tree>
            <el-empty v-else :image-size="54" description="暂无文件夹" />
          </aside>

          <div class="file-results">
            <section v-if="selectedProject" class="directory-context" aria-label="当前文件目录">
              <el-breadcrumb separator="/">
                <el-breadcrumb-item>
                  <button type="button" class="breadcrumb-button" @click="selectFolder(undefined)">
                    {{ selectedProject.name }}
                  </button>
                </el-breadcrumb-item>
                <el-breadcrumb-item v-if="queryParams.folder !== undefined">
                  <button
                    type="button"
                    class="breadcrumb-button"
                    :class="{ current: queryParams.folder === 'root' }"
                    @click="selectFolder('root')"
                  >
                    根目录
                  </button>
                </el-breadcrumb-item>
                <el-breadcrumb-item v-for="folder in currentFolderTrail" :key="folder.id">
                  <button
                    type="button"
                    class="breadcrumb-button"
                    :class="{ current: folder.id === queryParams.folder }"
                    @click="selectFolder(folder.id)"
                  >
                    {{ folder.name }}
                  </button>
                </el-breadcrumb-item>
                <el-breadcrumb-item v-if="queryParams.folder === undefined">全部目录汇总</el-breadcrumb-item>
              </el-breadcrumb>

              <div class="directory-current-row">
                <div class="directory-current-copy">
                  <span>{{ queryParams.folder === undefined ? '当前视图' : '当前目录' }}</span>
                  <strong>{{ currentFolderLabel }}</strong>
                  <p>{{ currentFolderHelp }}</p>
                </div>
                <div v-if="canManageSelectedProject" class="directory-actions">
                  <el-button :icon="FolderAdd" @click="openFolderDialog()">
                    {{ newFolderActionLabel }}
                  </el-button>
                  <el-button type="primary" :icon="Upload" @click="openUploadDialog">
                    上传到{{ operationDirectoryLabel }}
                  </el-button>
                </div>
              </div>
            </section>

            <section v-if="selectedProject && childFolders.length" class="child-folder-section">
              <div class="child-folder-heading">
                <strong>{{ queryParams.folder === undefined ? '可进入的根目录' : '下级目录' }}</strong>
                <span>点击文件夹进入，不会上传文件</span>
              </div>
              <div class="child-folder-grid">
                <button
                  v-for="folder in childFolders"
                  :key="folder.id"
                  type="button"
                  class="child-folder-card"
                  @click="selectFolder(folder.id)"
                >
                  <el-icon><Folder /></el-icon>
                  <span>
                    <strong>{{ folder.name }}</strong>
                    <small>{{ folder.file_count }} 个直接文件</small>
                  </span>
                  <em>进入</em>
                </button>
              </div>
            </section>

            <div class="list-heading">
              <div>
                <h2>{{ currentFolderLabel }}</h2>
                <span v-if="sensitiveCount > 0" class="sensitive-count">{{ sensitiveCount }} 个敏感文件</span>
              </div>
              <span>{{ fileList.length }} 个当前结果</span>
            </div>

            <div
              v-if="!isMobile"
              class="file-table-shell"
              tabindex="0"
              aria-label="文件列表，可横向滚动"
            >
              <el-table
                v-loading="loading"
                :data="fileList"
                stripe
                size="small"
                :row-class-name="getFileRowClass"
              >
                <el-table-column prop="name" label="文件" min-width="220" show-overflow-tooltip>
                  <template #default="{ row }">
                    <div class="file-cell">
                      <span class="file-icon-box" :class="{ 'is-sensitive': row.level === 'sensitive' }">
                        <el-icon><Document /></el-icon>
                      </span>
                      <div>
                        <strong>{{ row.name }}</strong>
                        <span>{{ row.content_type || '未知类型' }}</span>
                      </div>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column prop="project_name" label="所属项目" min-width="130" show-overflow-tooltip>
                  <template #default="{ row }">{{ row.project_name || '-' }}</template>
                </el-table-column>
                <el-table-column prop="folder_name" label="文件夹" min-width="110" show-overflow-tooltip>
                  <template #default="{ row }">{{ row.folder_name || '根目录' }}</template>
                </el-table-column>
                <el-table-column label="可见范围" min-width="145" show-overflow-tooltip>
                  <template #default="{ row }">{{ fileVisibilityLabel(row as ManagedFileAsset) }}</template>
                </el-table-column>
                <el-table-column label="标签" min-width="160">
                  <template #default="{ row }">
                    <div v-if="row.tags?.length" class="file-tags">
                      <el-tag
                        v-for="tag in row.tags.slice(0, 3)"
                        :key="tag.id"
                        size="small"
                        effect="plain"
                        :style="tagStyle(tag.color)"
                      >
                        {{ tag.name }}
                      </el-tag>
                      <span v-if="row.tags.length > 3" class="tag-more">+{{ row.tags.length - 3 }}</span>
                    </div>
                    <span v-else class="muted-value">-</span>
                  </template>
                </el-table-column>
                <el-table-column prop="size" label="大小" width="90">
                  <template #default="{ row }">{{ formatFileSize(row.size) }}</template>
                </el-table-column>
                <el-table-column prop="level" label="级别" width="90">
                  <template #default="{ row }">
                    <el-tag :type="FILE_LEVEL_MAP[row.level]?.tagType as any" size="small" effect="plain">
                      {{ FILE_LEVEL_MAP[row.level]?.label || row.level_display || row.level }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="created_at" label="上传时间" width="112">
                  <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
                </el-table-column>
                <el-table-column label="操作" width="170" fixed="right" align="right">
                  <template #default="{ row }">
                    <el-tooltip content="预览" placement="top">
                      <el-button text :icon="View" aria-label="预览" @click="handlePreview(row as ManagedFileAsset)" />
                    </el-tooltip>
                    <el-tooltip content="下载" placement="top">
                      <el-button text type="primary" :icon="Download" aria-label="下载" @click="handleDownload(row as ManagedFileAsset)" />
                    </el-tooltip>
                    <el-tooltip content="版本历史" placement="top">
                      <el-button text :icon="Clock" aria-label="版本历史" @click="openVersionDialog(row as ManagedFileAsset)" />
                    </el-tooltip>
                    <el-dropdown trigger="click" @command="handleFileCommand($event, row as ManagedFileAsset)">
                      <el-button text :icon="MoreFilled" aria-label="更多操作" />
                      <template #dropdown>
                        <el-dropdown-menu>
                          <el-dropdown-item command="tags" :icon="CollectionTag">标签</el-dropdown-item>
                          <el-dropdown-item v-if="row.level !== 'sensitive'" command="share" :icon="Share">分享</el-dropdown-item>
                          <el-dropdown-item v-if="canManageFile(row as ManagedFileAsset)" command="move" :icon="FolderOpened">移动</el-dropdown-item>
                          <el-dropdown-item v-if="canManageFile(row as ManagedFileAsset)" command="delete" :icon="Delete" divided>移入回收站</el-dropdown-item>
                        </el-dropdown-menu>
                      </template>
                    </el-dropdown>
                  </template>
                </el-table-column>
                <template #empty><el-empty description="暂无文件" /></template>
              </el-table>
            </div>

            <div v-else v-loading="loading" class="mobile-file-list">
              <article
                v-for="item in fileList"
                :key="item.id"
                class="mobile-file-card"
                :class="{ 'is-sensitive': item.level === 'sensitive' }"
              >
                <div class="mobile-file-heading">
                  <div class="mobile-file-title">
                    <span class="file-icon-box" :class="{ 'is-sensitive': item.level === 'sensitive' }">
                      <el-icon><Document /></el-icon>
                    </span>
                    <div><h3>{{ item.name }}</h3><span>{{ item.content_type || '未知类型' }}</span></div>
                  </div>
                  <el-tag :type="FILE_LEVEL_MAP[item.level]?.tagType as any" size="small" effect="plain">
                    {{ FILE_LEVEL_MAP[item.level]?.label || item.level_display || item.level }}
                  </el-tag>
                </div>
                <div v-if="item.tags?.length" class="file-tags mobile-tags">
                  <el-tag
                    v-for="tag in item.tags"
                    :key="tag.id"
                    size="small"
                    effect="plain"
                    :style="tagStyle(tag.color)"
                  >
                    {{ tag.name }}
                  </el-tag>
                </div>
                <dl class="mobile-file-meta">
                  <div class="meta-wide"><dt>所属项目</dt><dd>{{ item.project_name || '-' }}</dd></div>
                  <div><dt>文件夹</dt><dd>{{ item.folder_name || '根目录' }}</dd></div>
                  <div class="meta-wide"><dt>可见范围</dt><dd>{{ fileVisibilityLabel(item) }}</dd></div>
                  <div><dt>大小</dt><dd>{{ formatFileSize(item.size) }}</dd></div>
                  <div><dt>上传者</dt><dd>{{ item.uploader_name || '-' }}</dd></div>
                  <div><dt>上传时间</dt><dd>{{ formatDate(item.created_at) }}</dd></div>
                </dl>
                <div class="mobile-file-actions">
                  <el-tooltip content="预览" placement="top">
                    <el-button text :icon="View" aria-label="预览" @click="handlePreview(item)" />
                  </el-tooltip>
                  <el-tooltip content="下载" placement="top">
                    <el-button text type="primary" :icon="Download" aria-label="下载" @click="handleDownload(item)" />
                  </el-tooltip>
                  <el-tooltip content="版本历史" placement="top">
                    <el-button text :icon="Clock" aria-label="版本历史" @click="openVersionDialog(item)" />
                  </el-tooltip>
                  <el-dropdown trigger="click" @command="handleFileCommand($event, item)">
                    <el-button text :icon="MoreFilled" aria-label="更多操作" />
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="tags" :icon="CollectionTag">标签</el-dropdown-item>
                        <el-dropdown-item v-if="item.level !== 'sensitive'" command="share" :icon="Share">分享</el-dropdown-item>
                        <el-dropdown-item v-if="canManageFile(item)" command="move" :icon="FolderOpened">移动</el-dropdown-item>
                        <el-dropdown-item v-if="canManageFile(item)" command="delete" :icon="Delete" divided>移入回收站</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </article>
              <el-empty v-if="fileList.length === 0 && !loading" description="暂无文件" />
            </div>

            <div v-if="total > 0" class="pagination-wrapper">
              <AccessiblePagination
                v-model:current-page="queryParams.page"
                v-model:page-size="queryParams.page_size"
                :total="total"
                :page-sizes="[10, 20, 50]"
                :layout="isMobile ? 'prev, pager, next' : 'total, sizes, prev, pager, next'"
                background
                @size-change="loadData"
                @current-change="loadData"
              />
            </div>
          </div>
        </div>
      </section>
    </template>

    <section v-else class="trash-workspace">
      <div class="list-heading">
        <div><h2>文件回收站</h2></div>
        <el-button :icon="Refresh" :loading="trashLoading" @click="loadRecycleBin">刷新</el-button>
      </div>
      <div
        v-if="!isMobile"
        class="file-table-shell"
        tabindex="0"
        aria-label="回收站文件列表，可横向滚动"
      >
        <el-table v-loading="trashLoading" :data="recycledFiles" size="small">
          <el-table-column prop="name" label="文件" min-width="220" show-overflow-tooltip />
          <el-table-column prop="project_name" label="所属项目" min-width="150">
            <template #default="{ row }">{{ row.project_name || '-' }}</template>
          </el-table-column>
          <el-table-column prop="size" label="大小" width="100">
            <template #default="{ row }">{{ formatFileSize(row.size) }}</template>
          </el-table-column>
          <el-table-column prop="deleted_by_name" label="删除人" width="110">
            <template #default="{ row }">{{ row.deleted_by_name || '-' }}</template>
          </el-table-column>
          <el-table-column prop="deleted_at" label="删除时间" min-width="150">
            <template #default="{ row }">{{ formatDate(row.deleted_at) }}</template>
          </el-table-column>
          <el-table-column v-if="canRestoreFiles" label="操作" width="140" align="right">
            <template #default="{ row }">
              <el-button text type="primary" :icon="RefreshLeft" @click="handleRestore(row as ManagedFileAsset)">恢复</el-button>
              <el-button
                v-if="canPermanentlyDelete"
                text
                type="danger"
                :icon="Delete"
                @click="handlePermanentDelete(row as ManagedFileAsset)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
          <template #empty><el-empty description="回收站为空" /></template>
        </el-table>
      </div>
      <div v-else v-loading="trashLoading" class="mobile-file-list">
        <article v-for="item in recycledFiles" :key="item.id" class="mobile-file-card trash-card">
          <div class="mobile-file-title">
            <span class="file-icon-box"><el-icon><Document /></el-icon></span>
            <div><h3>{{ item.name }}</h3><span>{{ item.project_name || '-' }}</span></div>
          </div>
          <dl class="mobile-file-meta">
            <div><dt>大小</dt><dd>{{ formatFileSize(item.size) }}</dd></div>
            <div><dt>删除人</dt><dd>{{ item.deleted_by_name || '-' }}</dd></div>
            <div class="meta-wide"><dt>删除时间</dt><dd>{{ formatDate(item.deleted_at) }}</dd></div>
          </dl>
          <div v-if="canRestoreFiles" class="mobile-file-actions">
            <el-button text type="primary" :icon="RefreshLeft" @click="handleRestore(item)">恢复</el-button>
            <el-button v-if="canPermanentlyDelete" text type="danger" :icon="Delete" @click="handlePermanentDelete(item)">删除</el-button>
          </div>
        </article>
        <el-empty v-if="recycledFiles.length === 0 && !trashLoading" description="回收站为空" />
      </div>
    </section>

    <el-dialog
      v-model="uploadVisible"
      :title="`上传文件到：${uploadTargetLabel}`"
      width="min(520px, calc(100vw - 32px))"
      :close-on-click-modal="!uploading"
    >
      <el-form label-position="top">
        <el-form-item label="项目" required>
          <el-select v-model="uploadForm.project" filterable @change="handleUploadProjectChange">
            <el-option v-for="project in manageableProjects" :key="project.id" :label="project.name" :value="project.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="上传位置" required>
          <el-select v-model="uploadForm.folder" clearable placeholder="项目根目录">
            <el-option v-for="folder in uploadFolders" :key="folder.id" :label="folder.path" :value="folder.id" />
          </el-select>
          <p class="form-help">清空选择表示上传到项目根目录；选择文件夹后，文件会实际关联到该目录。</p>
        </el-form-item>
        <el-form-item label="访问级别" required>
          <el-radio-group v-model="uploadForm.level">
            <el-radio-button value="public">全实践团队</el-radio-button>
            <el-radio-button value="internal">本项目成员</el-radio-button>
            <el-radio-button value="sensitive">敏感审批</el-radio-button>
          </el-radio-group>
          <p class="form-help">
            “全实践团队”仍需登录；互联网公开只通过公开门户或单独创建的分享链接。
          </p>
        </el-form-item>
        <el-form-item v-if="uploadForm.level === 'internal'" label="内部可见范围" required>
          <el-radio-group v-model="uploadForm.scope" @change="handleUploadScopeChange">
            <el-radio-button value="project">本项目成员</el-radio-button>
            <el-radio-button value="team">指定小团队</el-radio-button>
            <el-radio-button value="competition">指定参赛条目</el-radio-button>
          </el-radio-group>
          <el-select
            v-if="uploadForm.scope === 'team'"
            v-model="uploadForm.team"
            class="scope-target-select"
            clearable
            placeholder="请选择项目关联团队"
          >
            <el-option
              v-for="team in uploadTeamOptions"
              :key="team.id"
              :label="team.parent_name ? `${team.parent_name} / ${team.name}` : team.name"
              :value="team.id"
            />
          </el-select>
          <el-select
            v-if="uploadForm.scope === 'competition'"
            v-model="uploadForm.competition_entry"
            class="scope-target-select"
            clearable
            filterable
            :loading="uploadCompetitionLoading"
            placeholder="请选择比赛与参赛条目"
          >
            <el-option
              v-for="entry in uploadCompetitionOptions"
              :key="entry.id"
              :label="[entry.event_name || entry.name, entry.entry_name].filter(Boolean).join(' · ')"
              :value="entry.id"
            />
          </el-select>
          <p class="form-help">指定范围后，其他项目成员也无法通过文件列表或下载接口访问。</p>
        </el-form-item>
        <el-form-item label="文件" required>
          <el-upload
            :key="uploadPickerKey"
            drag
            :auto-upload="false"
            :limit="1"
            :on-change="handleUploadFileChange"
            :on-exceed="handleUploadExceed"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="upload-label">选择文件</div>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="uploading" @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUploadSubmit">
          上传到所选目录
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="folderDialogVisible"
      :title="folderDialogTitle"
      width="min(460px, calc(100vw - 32px))"
    >
      <el-form label-position="top">
        <el-alert
          v-if="!editingFolder"
          :title="`将在「${folderParentLabel}」下新建文件夹，不会上传文件。`"
          type="info"
          :closable="false"
          show-icon
        />
        <el-form-item label="文件夹名称" required>
          <el-input v-model="folderForm.name" maxlength="100" show-word-limit @keyup.enter="handleFolderSubmit" />
        </el-form-item>
        <el-form-item label="所在目录">
          <el-select v-model="folderForm.parent" clearable placeholder="项目根目录">
            <el-option
              v-for="folder in folderParentOptions"
              :key="folder.id"
              :label="folder.path"
              :value="folder.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="folderDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="folderSaving" @click="handleFolderSubmit">
          {{ editingFolder ? '保存修改' : '新建到此目录' }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="tagManagerVisible"
      title="标签管理"
      width="min(620px, calc(100vw - 32px))"
    >
      <div class="tag-editor">
        <el-input v-model="tagForm.name" maxlength="50" placeholder="标签名称" @keyup.enter="handleTagSave" />
        <el-color-picker v-model="tagForm.color" />
        <el-button type="primary" :loading="tagSaving" @click="handleTagSave">
          {{ editingTagId ? '更新' : '创建' }}
        </el-button>
        <el-button v-if="editingTagId" @click="resetTagForm">取消</el-button>
      </div>
      <div class="tag-list">
        <div v-for="tag in projectTags" :key="tag.id" class="tag-row">
          <div>
            <span class="tag-swatch" :style="{ backgroundColor: tag.color }"></span>
            <strong>{{ tag.name }}</strong>
          </div>
          <div>
            <el-tooltip content="编辑标签" placement="top">
              <el-button text :icon="Edit" aria-label="编辑标签" @click="editTag(tag)" />
            </el-tooltip>
            <el-tooltip content="删除标签" placement="top">
              <el-button text type="danger" :icon="Delete" aria-label="删除标签" @click="handleTagDelete(tag)" />
            </el-tooltip>
          </div>
        </div>
        <el-empty v-if="projectTags.length === 0" :image-size="64" description="暂无项目标签" />
      </div>
    </el-dialog>

    <el-dialog
      v-model="tagAssignVisible"
      :title="`${tagAssignFile?.name || '文件'} · 标签`"
      width="min(520px, calc(100vw - 32px))"
    >
      <div v-loading="tagAssignLoading" class="tag-checkbox-list">
        <el-checkbox-group v-model="selectedTagIds">
          <el-checkbox v-for="tag in assignableTags" :key="tag.id" :value="tag.id">
            <span class="tag-swatch" :style="{ backgroundColor: tag.color }"></span>
            {{ tag.name }}
          </el-checkbox>
        </el-checkbox-group>
        <el-empty v-if="assignableTags.length === 0 && !tagAssignLoading" :image-size="64" description="暂无可用标签" />
      </div>
      <template #footer>
        <el-button @click="tagAssignVisible = false">取消</el-button>
        <el-button
          type="primary"
          :disabled="!tagAssignFile || !canManageFile(tagAssignFile)"
          :loading="tagAssignSaving"
          @click="handleTagAssignSave"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="moveVisible"
      :title="`${moveTarget?.name || '文件'} · 移动`"
      width="min(460px, calc(100vw - 32px))"
    >
      <el-form label-position="top">
        <el-form-item label="目标文件夹">
          <el-select v-model="moveFolderId" clearable placeholder="项目根目录">
            <el-option v-for="folder in moveFolders" :key="folder.id" :label="folder.path" :value="folder.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="moveVisible = false">取消</el-button>
        <el-button type="primary" :loading="moveSaving" @click="handleMoveSave">移动</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="shareVisible"
      :title="`${shareFile?.name || '文件'} · 分享`"
      width="min(720px, calc(100vw - 32px))"
    >
      <div class="share-create-row">
        <el-date-picker
          v-model="shareForm.expire_at"
          type="datetime"
          value-format="YYYY-MM-DDTHH:mm:ss"
          placeholder="过期时间"
          clearable
        />
        <el-input-number v-model="shareForm.max_views" :min="1" :max="100000" placeholder="访问次数" />
        <el-button type="primary" :loading="shareCreating" :icon="Link" @click="handleShareCreate">创建链接</el-button>
      </div>
      <div v-loading="shareLoading" class="share-list">
        <div v-for="link in shareLinks" :key="link.id" class="share-row">
          <div class="share-main">
            <div>
              <code>{{ link.token.slice(0, 12) }}</code>
              <el-tag :type="link.is_valid ? 'success' : 'info'" size="small" effect="plain">
                {{ link.is_valid ? '有效' : '失效' }}
              </el-tag>
            </div>
            <span>
              {{ link.view_count }}{{ link.max_views ? ` / ${link.max_views}` : '' }} 次
              <template v-if="link.expire_at"> · {{ formatDate(link.expire_at) }}</template>
            </span>
          </div>
          <div class="share-actions">
            <el-tooltip content="复制链接" placement="top">
              <el-button text :icon="CopyDocument" aria-label="复制链接" @click="copyShareLink(link)" />
            </el-tooltip>
            <el-button v-if="link.is_active" text type="danger" @click="handleShareRevoke(link)">撤销</el-button>
          </div>
        </div>
        <el-empty v-if="shareLinks.length === 0 && !shareLoading" :image-size="64" description="暂无分享链接" />
      </div>
    </el-dialog>

    <el-dialog
      v-model="previewVisible"
      :title="previewFile?.name || '文件预览'"
      width="min(1040px, calc(100vw - 32px))"
      top="4vh"
      @close="handlePreviewClose"
    >
      <div v-if="previewFile?.level === 'sensitive'" class="sensitive-preview-alert">
        <el-icon><WarningFilled /></el-icon>
        <span>敏感文件</span>
      </div>
      <div v-if="previewLoading" v-loading="true" class="preview-loading"></div>
      <div v-else-if="previewType === 'office' && officePreview" class="office-preview">
        <el-alert v-if="officePreview.truncated" title="预览内容已按安全上限截取" type="warning" :closable="false" />
        <section v-for="(section, sectionIndex) in officePreview.sections" :key="`${section.title}-${sectionIndex}`" class="office-section">
          <h3>{{ section.title }}</h3>
          <p v-for="(paragraph, paragraphIndex) in section.paragraphs" :key="paragraphIndex">{{ paragraph }}</p>
          <div v-for="(table, tableIndex) in section.tables" :key="tableIndex" class="office-table-shell">
            <table>
              <tbody>
                <tr v-for="(row, rowIndex) in table" :key="rowIndex">
                  <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
        <el-empty v-if="officePreview.sections.length === 0" description="文档没有可显示的文本内容" />
      </div>
      <div v-else-if="previewUrl" class="preview-container">
        <img v-if="previewType === 'image'" :src="previewUrl" class="preview-image" alt="预览" />
        <iframe v-else-if="previewType === 'pdf'" :src="previewUrl" class="preview-iframe" title="PDF预览" sandbox=""></iframe>
        <video v-else-if="previewType === 'video'" :src="previewUrl" controls class="preview-video"></video>
        <audio v-else-if="previewType === 'audio'" :src="previewUrl" controls class="preview-audio"></audio>
      </div>
      <el-empty v-else description="该文件类型不支持在线预览" />
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
        <el-button :icon="Download" type="primary" :disabled="!previewFile" @click="previewFile && handleDownload(previewFile)">下载</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="versionVisible"
      :title="`${versionFile?.name || '文件'} · 版本历史`"
      width="min(760px, calc(100vw - 32px))"
    >
      <div class="version-toolbar">
        <strong>当前版本 v{{ versionFile?.version || 1 }}</strong>
        <el-upload
          v-if="versionFile && canManageFile(versionFile)"
          :auto-upload="false"
          :show-file-list="false"
          :on-change="handleVersionUpload"
        >
          <el-button type="primary" :icon="Upload" :loading="versionUploading">上传新版本</el-button>
        </el-upload>
      </div>
      <el-table v-loading="versionLoading" :data="versions" size="small">
        <template #empty><el-empty description="暂无历史版本" /></template>
        <el-table-column prop="version" label="版本" width="90">
          <template #default="{ row }">v{{ row.version }}</template>
        </el-table-column>
        <el-table-column prop="uploader_name" label="上传者" min-width="120">
          <template #default="{ row }">{{ row.uploader_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="归档时间" min-width="150">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleVersionDownload(row as FileVersion)">下载</el-button>
            <el-button
              v-if="versionFile && canManageFile(versionFile)"
              link
              type="warning"
              @click="handleVersionRestore(row as FileVersion)"
            >
              恢复
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox, type UploadFile } from 'element-plus'
import {
  Clock,
  CollectionTag,
  CopyDocument,
  Delete,
  Document,
  Download,
  Edit,
  Folder,
  FolderAdd,
  FolderOpened,
  Link,
  MoreFilled,
  Plus,
  Refresh,
  RefreshLeft,
  Search,
  Share,
  Upload,
  UploadFilled,
  View,
  WarningFilled,
} from '@element-plus/icons-vue'
import {
  buildFileShareUrl,
  createFileFolder,
  createFileShareLink,
  createFileTag,
  deleteFile,
  deleteFileFolder,
  deleteFileTag,
  downloadFile,
  downloadFileVersion,
  getFile,
  getFileFolders,
  getFiles,
  getFileShareLinks,
  getFileTagRelations,
  getFileTags,
  getFileVersions,
  getOfficePreview,
  getRecycledFiles,
  moveFile,
  permanentlyDeleteFile,
  replaceFileTags,
  restoreFileVersion,
  restoreRecycledFile,
  revokeFileShareLink,
  updateFileFolder,
  updateFileTag,
  uploadFile,
  uploadFileVersion,
  type FileFolder,
  type FileManagementQueryParams,
  type FileShareLink,
  type FileTag,
  type ManagedFileAsset,
  type OfficePreview,
} from '@/api/files'
import { getProjects } from '@/api/projects'
import { getCompetitions } from '@/api/competitions'
import { getTeams, type Team } from '@/api/teams'
import PageHeader from '@/components/PageHeader.vue'
import { useDevice } from '@/composables/useDevice'
import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'
import type { Competition, FileLevel, FileVersion, Project } from '@/types'
import { FILE_LEVEL_MAP } from '@/utils/constants'
import { downloadBlob, formatDate, formatFileSize } from '@/utils/format'
import { positiveQueryId } from '@/utils/globalSearch'

const route = useRoute()

interface FolderTreeNode extends FileFolder {
  children: FolderTreeNode[]
}

type WorkspaceMode = 'files' | 'trash'
type PreviewType = 'image' | 'pdf' | 'video' | 'audio' | 'office' | 'unknown'

const appStore = useAppStore()
const userStore = useUserStore()
const { isMobile } = useDevice()

const workspaceMode = ref<WorkspaceMode>('files')
const loading = ref(false)
const fileList = ref<ManagedFileAsset[]>([])
const total = ref(0)
const projectOptions = ref<Project[]>([])
const teamOptions = ref<Team[]>([])
const folders = ref<FileFolder[]>([])
const tags = ref<FileTag[]>([])

const queryParams = reactive<FileManagementQueryParams>({
  page: 1,
  page_size: appStore.itemsPerPage,
  project: undefined,
  folder: undefined,
  tag: undefined,
  level: undefined,
  search: '',
})

const selectedProject = computed(() =>
  projectOptions.value.find((project) => project.id === queryParams.project),
)
function projectTeamRootIds(project: Project): Set<number> {
  return new Set((project.team_details || []).map((team) => team.parent_id || team.id))
}

function hasManageableProjectTeam(project: Project): boolean {
  const rootIds = projectTeamRootIds(project)
  return rootIds.size > 0 && teamOptions.value.some((team) => (
    team.can_manage && rootIds.has(team.parent || team.id)
  ))
}

const manageableProjects = computed(() => projectOptions.value.filter((project) =>
  ['teacher', 'sys_admin'].includes(userStore.role)
  || project.can_manage
  || hasManageableProjectTeam(project),
))
const canManageSelectedProject = computed(() => Boolean(
  selectedProject.value
  && (
    ['teacher', 'sys_admin'].includes(userStore.role)
    || selectedProject.value.can_manage
  ),
))
const canUpload = computed(() =>
  Boolean(
    selectedProject.value
    && manageableProjects.value.some((project) => project.id === selectedProject.value?.id),
  ),
)
const canRestoreFiles = computed(() => ['teacher', 'sys_admin'].includes(userStore.role))
const canPermanentlyDelete = computed(() => userStore.role === 'sys_admin')
const canViewRecycle = computed(() => !['external', 'exited'].includes(
  userStore.userInfo?.membership_status || 'active',
))
const sensitiveCount = computed(() => fileList.value.filter((item) => item.level === 'sensitive').length)
const availableTags = computed(() => tags.value.filter((tag) =>
  tag.project == null || tag.project === queryParams.project,
))
const projectTags = computed(() => tags.value.filter((tag) => tag.project === queryParams.project))
const currentFolder = computed(() => (
  typeof queryParams.folder === 'number'
    ? folders.value.find((folder) => folder.id === queryParams.folder)
    : undefined
))
const currentFolderLabel = computed(() => {
  if (queryParams.folder === 'root') return '项目根目录'
  if (currentFolder.value) return currentFolder.value.path
  return selectedProject.value ? '全部目录汇总' : '全部项目文件'
})
const currentFolderTrail = computed<FileFolder[]>(() => {
  if (!currentFolder.value) return []
  const trail: FileFolder[] = []
  const byId = new Map(folders.value.map((folder) => [folder.id, folder]))
  let cursor: FileFolder | undefined = currentFolder.value
  while (cursor && trail.length < 8) {
    trail.unshift(cursor)
    cursor = cursor.parent ? byId.get(cursor.parent) : undefined
  }
  return trail
})
const childFolders = computed(() => {
  const parentId = typeof queryParams.folder === 'number' ? queryParams.folder : null
  return folders.value.filter((folder) => (folder.parent ?? null) === parentId)
})
const operationDirectoryLabel = computed(() =>
  currentFolder.value?.name || '项目根目录',
)
const uploadActionLabel = computed(() =>
  selectedProject.value ? `上传到${operationDirectoryLabel.value}` : '上传文件',
)
const newFolderActionLabel = computed(() =>
  currentFolder.value ? '新建子文件夹' : '新建文件夹',
)
const currentFolderHelp = computed(() => {
  if (queryParams.folder === undefined) {
    return '这是跨目录汇总视图；上传或新建默认放到项目根目录。先点击文件夹可进入指定目录。'
  }
  return `这里仅显示${operationDirectoryLabel.value}中的直接文件；上传和新建会默认使用当前目录。`
})
const folderTree = computed<FolderTreeNode[]>(() => {
  const nodes = new Map<number, FolderTreeNode>()
  folders.value.forEach((folder) => nodes.set(folder.id, { ...folder, children: [] }))
  const roots: FolderTreeNode[] = []
  nodes.forEach((node) => {
    const parent = node.parent ? nodes.get(node.parent) : undefined
    if (parent) parent.children.push(node)
    else roots.push(node)
  })
  return roots
})

function canManageFile(file: ManagedFileAsset): boolean {
  return Boolean(file.can_manage)
}

async function loadProjects(): Promise<void> {
  try {
    const response = await getProjects({ page: 1, page_size: 100 })
    projectOptions.value = response.results
  } catch {
    projectOptions.value = []
  }
}

async function loadTeams(): Promise<void> {
  try {
    const response = await getTeams({ page: 1, page_size: 200 })
    teamOptions.value = response.results
  } catch {
    teamOptions.value = []
  }
}

async function loadData(): Promise<void> {
  loading.value = true
  try {
    const response = await getFiles(queryParams)
    fileList.value = response.results
    total.value = response.count
  } finally {
    loading.value = false
  }
}

async function loadFolders(projectId = queryParams.project): Promise<FileFolder[]> {
  if (!projectId) {
    folders.value = []
    return []
  }
  const result = await getFileFolders(projectId)
  if (projectId === queryParams.project) folders.value = result
  return result
}

async function loadTags(): Promise<void> {
  tags.value = await getFileTags()
}

function handleSearch(): void {
  queryParams.page = 1
  void loadData()
}

async function handleProjectChange(): Promise<void> {
  queryParams.folder = undefined
  queryParams.tag = undefined
  queryParams.page = 1
  await Promise.all([loadFolders(), loadTags(), loadData()])
}

function handleReset(): void {
  queryParams.project = undefined
  queryParams.folder = undefined
  queryParams.tag = undefined
  queryParams.level = undefined
  queryParams.search = ''
  queryParams.page = 1
  folders.value = []
  void loadData()
}

function selectFolder(folder: number | 'root' | undefined): void {
  queryParams.folder = folder
  handleSearch()
}

function handleFolderNodeClick(folder: FileFolder): void {
  selectFolder(folder.id)
}

function handleWorkspaceChange(value: string | number | boolean | undefined): void {
  if (value === 'trash') void loadRecycleBin()
}

function getFileRowClass({ row }: { row: ManagedFileAsset }): string {
  return row.level === 'sensitive' ? 'sensitive-file-row' : ''
}

function tagStyle(color: string): Record<string, string> {
  return {
    color,
    borderColor: `${color}66`,
    backgroundColor: `${color}0f`,
  }
}

function fileVisibilityLabel(file: ManagedFileAsset): string {
  if (file.level === 'public') return '全实践团队'
  if (file.level === 'sensitive') return '敏感审批 / 授权'
  if (file.competition_entry) return `参赛条目：${file.competition_entry_name || file.competition_entry}`
  if (file.team) return `小团队：${file.team_name || file.team}`
  return '本项目成员'
}

async function handleDownload(file: ManagedFileAsset): Promise<void> {
  try {
    const blob = await downloadFile(file.id)
    downloadBlob(blob, file.name)
  } catch {
    ElMessage.error('下载失败')
  }
}

const uploadVisible = ref(false)
const uploading = ref(false)
const uploadPickerKey = ref(0)
const pendingUpload = ref<File | null>(null)
const uploadFolders = ref<FileFolder[]>([])
const uploadCompetitionOptions = ref<Competition[]>([])
const uploadCompetitionLoading = ref(false)
const uploadForm = reactive<{
  project?: number
  folder?: number
  level: FileLevel
  scope: 'project' | 'team' | 'competition'
  team?: number
  competition_entry?: number
}>({
  project: undefined,
  folder: undefined,
  level: 'internal',
  scope: 'project',
  team: undefined,
  competition_entry: undefined,
})
const uploadTeamOptions = computed(() => {
  const project = projectOptions.value.find((item) => item.id === uploadForm.project)
  if (!project) return []
  const rootIds = projectTeamRootIds(project)
  return teamOptions.value.filter((team) => (
    team.can_manage && rootIds.has(team.parent || team.id)
  ))
})
const uploadTargetLabel = computed(() => {
  const project = projectOptions.value.find((item) => item.id === uploadForm.project)
  const folder = uploadFolders.value.find((item) => item.id === uploadForm.folder)
  if (!project) return '请先选择项目'
  return `${project.name} / ${folder?.path || '根目录'}`
})

async function openUploadDialog(): Promise<void> {
  uploadForm.project = queryParams.project
  uploadForm.folder = typeof queryParams.folder === 'number' ? queryParams.folder : undefined
  uploadForm.level = 'internal'
  const canUseProjectScope = Boolean(
    ['teacher', 'sys_admin'].includes(userStore.role)
    || projectOptions.value.find((item) => item.id === uploadForm.project)?.can_manage,
  )
  uploadForm.scope = canUseProjectScope ? 'project' : 'team'
  uploadForm.team = canUseProjectScope ? undefined : uploadTeamOptions.value[0]?.id
  uploadForm.competition_entry = undefined
  pendingUpload.value = null
  uploadPickerKey.value += 1
  uploadFolders.value = queryParams.project ? folders.value : []
  await loadUploadCompetitions(uploadForm.project)
  uploadVisible.value = true
}

async function handleUploadProjectChange(projectId: number): Promise<void> {
  uploadForm.folder = undefined
  uploadForm.competition_entry = undefined
  const project = projectOptions.value.find((item) => item.id === projectId)
  const canUseProjectScope = Boolean(
    ['teacher', 'sys_admin'].includes(userStore.role) || project?.can_manage,
  )
  uploadForm.scope = canUseProjectScope ? 'project' : 'team'
  uploadForm.team = canUseProjectScope ? undefined : uploadTeamOptions.value[0]?.id
  uploadFolders.value = projectId ? await getFileFolders(projectId) : []
  await loadUploadCompetitions(projectId)
}

function handleUploadScopeChange(): void {
  uploadForm.team = undefined
  uploadForm.competition_entry = undefined
}

async function loadUploadCompetitions(projectId?: number): Promise<void> {
  uploadCompetitionOptions.value = []
  if (!projectId) return
  uploadCompetitionLoading.value = true
  try {
    const response = await getCompetitions({ project: projectId, page: 1, page_size: 200 })
    uploadCompetitionOptions.value = response.results
  } finally {
    uploadCompetitionLoading.value = false
  }
}

function handleUploadFileChange(file: UploadFile): void {
  pendingUpload.value = file.raw || null
}

function handleUploadExceed(): void {
  ElMessage.warning('一次只能上传一个文件')
}

async function handleUploadSubmit(): Promise<void> {
  if (!uploadForm.project || !pendingUpload.value) {
    ElMessage.warning('请选择项目和文件')
    return
  }
  if (uploadForm.level === 'internal' && uploadForm.scope === 'team' && !uploadForm.team) {
    ElMessage.warning('请选择指定小团队')
    return
  }
  if (
    uploadForm.level === 'internal'
    && uploadForm.scope === 'competition'
    && !uploadForm.competition_entry
  ) {
    ElMessage.warning('请选择指定参赛条目')
    return
  }
  uploading.value = true
  try {
    await uploadFile(uploadForm.project, pendingUpload.value, {
      project: uploadForm.project,
      folder: uploadForm.folder,
      level: uploadForm.level,
      team: uploadForm.level === 'internal' && uploadForm.scope === 'team'
        ? uploadForm.team
        : undefined,
      competition_entry: uploadForm.level === 'internal' && uploadForm.scope === 'competition'
        ? uploadForm.competition_entry
        : undefined,
    })
    uploadVisible.value = false
    ElMessage.success('文件上传成功')
    if (queryParams.project === uploadForm.project) {
      await Promise.all([loadData(), loadFolders()])
    }
  } finally {
    uploading.value = false
  }
}

const folderDialogVisible = ref(false)
const folderSaving = ref(false)
const editingFolder = ref<FileFolder | null>(null)
const folderForm = reactive<{ name: string; parent?: number }>({ name: '', parent: undefined })
const folderParentLabel = computed(() => {
  const projectName = selectedProject.value?.name || '当前项目'
  const parent = folders.value.find((folder) => folder.id === folderForm.parent)
  return `${projectName} / ${parent?.path || '根目录'}`
})
const folderDialogTitle = computed(() => {
  if (editingFolder.value) return '编辑文件夹'
  return `新建文件夹到：${folderParentLabel.value}`
})
const folderParentOptions = computed(() => folders.value.filter((folder) => {
  if (!editingFolder.value) return true
  if (folder.id === editingFolder.value.id) return false
  const prefix = `${editingFolder.value.path} / `
  return !folder.path.startsWith(prefix)
}))

function openFolderDialog(folder?: FileFolder, parent?: number): void {
  editingFolder.value = folder || null
  folderForm.name = folder?.name || ''
  folderForm.parent = folder
    ? folder.parent ?? undefined
    : parent ?? (typeof queryParams.folder === 'number' ? queryParams.folder : undefined)
  folderDialogVisible.value = true
}

async function handleFolderSubmit(): Promise<void> {
  const name = folderForm.name.trim()
  if (!queryParams.project || !name) {
    ElMessage.warning('请输入文件夹名称')
    return
  }
  folderSaving.value = true
  try {
    if (editingFolder.value) {
      await updateFileFolder(editingFolder.value.id, {
        name,
        parent: folderForm.parent || null,
      })
    } else {
      await createFileFolder({
        project: queryParams.project,
        name,
        parent: folderForm.parent || null,
      })
    }
    folderDialogVisible.value = false
    await loadFolders()
    ElMessage.success(editingFolder.value ? '文件夹已更新' : '文件夹已创建')
  } finally {
    folderSaving.value = false
  }
}

async function handleFolderDelete(folder: FileFolder): Promise<void> {
  await ElMessageBox.confirm(`确定删除文件夹「${folder.name}」吗？`, '删除文件夹', { type: 'warning' })
  await deleteFileFolder(folder.id)
  if (queryParams.folder === folder.id) queryParams.folder = 'root'
  await Promise.all([loadFolders(), loadData()])
  ElMessage.success('文件夹已删除')
}

const tagManagerVisible = ref(false)
const tagSaving = ref(false)
const editingTagId = ref<number | null>(null)
const tagForm = reactive({ name: '', color: '#409EFF' })

function openTagManager(): void {
  resetTagForm()
  tagManagerVisible.value = true
}

function resetTagForm(): void {
  editingTagId.value = null
  tagForm.name = ''
  tagForm.color = '#409EFF'
}

function editTag(tag: FileTag): void {
  editingTagId.value = tag.id
  tagForm.name = tag.name
  tagForm.color = tag.color
}

async function handleTagSave(): Promise<void> {
  const name = tagForm.name.trim()
  if (!queryParams.project || !name) {
    ElMessage.warning('请输入标签名称')
    return
  }
  tagSaving.value = true
  try {
    if (editingTagId.value) {
      await updateFileTag(editingTagId.value, { name, color: tagForm.color })
    } else {
      await createFileTag({ name, color: tagForm.color, project: queryParams.project })
    }
    await Promise.all([loadTags(), loadData()])
    resetTagForm()
    ElMessage.success('标签已保存')
  } finally {
    tagSaving.value = false
  }
}

async function handleTagDelete(tag: FileTag): Promise<void> {
  await ElMessageBox.confirm(`确定删除标签「${tag.name}」吗？`, '删除标签', { type: 'warning' })
  await deleteFileTag(tag.id)
  await Promise.all([loadTags(), loadData()])
  ElMessage.success('标签已删除')
}

const tagAssignVisible = ref(false)
const tagAssignLoading = ref(false)
const tagAssignSaving = ref(false)
const tagAssignFile = ref<ManagedFileAsset | null>(null)
const selectedTagIds = ref<number[]>([])
const originalTagIds = ref<number[]>([])
const assignableTags = computed(() => tags.value.filter((tag) =>
  tag.project == null || tag.project === tagAssignFile.value?.project,
))

async function openTagAssign(file: ManagedFileAsset): Promise<void> {
  tagAssignFile.value = file
  tagAssignVisible.value = true
  tagAssignLoading.value = true
  try {
    const relations = await getFileTagRelations(file.id)
    originalTagIds.value = relations.map((relation) => relation.tag)
    selectedTagIds.value = [...originalTagIds.value]
  } finally {
    tagAssignLoading.value = false
  }
}

async function handleTagAssignSave(): Promise<void> {
  if (!tagAssignFile.value) return
  tagAssignSaving.value = true
  try {
    await replaceFileTags(tagAssignFile.value.id, originalTagIds.value, selectedTagIds.value)
    tagAssignVisible.value = false
    await loadData()
    ElMessage.success('文件标签已更新')
  } finally {
    tagAssignSaving.value = false
  }
}

const moveVisible = ref(false)
const moveSaving = ref(false)
const moveTarget = ref<ManagedFileAsset | null>(null)
const moveFolderId = ref<number | undefined>()
const moveFolders = ref<FileFolder[]>([])

async function openMoveDialog(file: ManagedFileAsset): Promise<void> {
  moveTarget.value = file
  moveFolderId.value = file.folder || undefined
  moveFolders.value = file.project ? await getFileFolders(file.project) : []
  moveVisible.value = true
}

async function handleMoveSave(): Promise<void> {
  if (!moveTarget.value) return
  moveSaving.value = true
  try {
    await moveFile(moveTarget.value.id, moveFolderId.value || null)
    moveVisible.value = false
    await Promise.all([loadData(), loadFolders()])
    ElMessage.success('文件已移动')
  } finally {
    moveSaving.value = false
  }
}

const shareVisible = ref(false)
const shareLoading = ref(false)
const shareCreating = ref(false)
const shareFile = ref<ManagedFileAsset | null>(null)
const shareLinks = ref<FileShareLink[]>([])
const shareForm = reactive<{ expire_at: string; max_views?: number }>({
  expire_at: '',
  max_views: undefined,
})

async function loadShareLinks(): Promise<void> {
  if (!shareFile.value) return
  shareLoading.value = true
  try {
    shareLinks.value = await getFileShareLinks(shareFile.value.id)
  } finally {
    shareLoading.value = false
  }
}

function openShareDialog(file: ManagedFileAsset): void {
  shareFile.value = file
  shareForm.expire_at = ''
  shareForm.max_views = undefined
  shareVisible.value = true
  void loadShareLinks()
}

async function handleShareCreate(): Promise<void> {
  if (!shareFile.value) return
  shareCreating.value = true
  try {
    const link = await createFileShareLink({
      file: shareFile.value.id,
      expire_at: shareForm.expire_at || null,
      max_views: shareForm.max_views || null,
    })
    await loadShareLinks()
    await copyShareLink(link)
    ElMessage.success('分享链接已创建并复制')
  } finally {
    shareCreating.value = false
  }
}

async function copyShareLink(link: FileShareLink): Promise<void> {
  const value = buildFileShareUrl(link.token)
  try {
    await navigator.clipboard.writeText(value)
  } catch {
    const textarea = document.createElement('textarea')
    textarea.value = value
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    textarea.remove()
  }
  ElMessage.success('链接已复制')
}

async function handleShareRevoke(link: FileShareLink): Promise<void> {
  await revokeFileShareLink(link.id)
  await loadShareLinks()
  ElMessage.success('分享链接已撤销')
}

async function handleDelete(file: ManagedFileAsset): Promise<void> {
  await ElMessageBox.confirm(`确定将文件「${file.name}」移入回收站吗？`, '删除文件', { type: 'warning' })
  await deleteFile(file.id)
  await Promise.all([loadData(), loadFolders()])
  ElMessage.success('文件已移入回收站')
}

function handleFileCommand(command: string | number | object, file: ManagedFileAsset): void {
  if (command === 'tags') void openTagAssign(file)
  if (command === 'share') openShareDialog(file)
  if (command === 'move') void openMoveDialog(file)
  if (command === 'delete') void handleDelete(file)
}

const recycledFiles = ref<ManagedFileAsset[]>([])
const trashLoading = ref(false)

async function loadRecycleBin(): Promise<void> {
  trashLoading.value = true
  try {
    recycledFiles.value = await getRecycledFiles()
  } finally {
    trashLoading.value = false
  }
}

async function handleRestore(file: ManagedFileAsset): Promise<void> {
  await restoreRecycledFile(file.id)
  await loadRecycleBin()
  ElMessage.success('文件已恢复')
}

async function handlePermanentDelete(file: ManagedFileAsset): Promise<void> {
  await ElMessageBox.confirm(`永久删除文件「${file.name}」？`, '永久删除', {
    type: 'error',
    confirmButtonText: '永久删除',
  })
  await permanentlyDeleteFile(file.id)
  await loadRecycleBin()
  ElMessage.success('文件已永久删除')
}

const previewVisible = ref(false)
const previewFile = ref<ManagedFileAsset | null>(null)
const previewUrl = ref('')
const previewType = ref<PreviewType>('unknown')
const previewLoading = ref(false)
const officePreview = ref<OfficePreview | null>(null)

function getPreviewType(file: ManagedFileAsset): PreviewType {
  const contentType = (file.content_type || '').toLowerCase()
  const name = (file.name || '').toLowerCase()
  if (contentType.startsWith('image/') || /\.(jpg|jpeg|png|gif|bmp|webp)$/.test(name)) return 'image'
  if (contentType === 'application/pdf' || name.endsWith('.pdf')) return 'pdf'
  if (contentType.startsWith('video/') || /\.(mp4|webm|ogg|mov)$/.test(name)) return 'video'
  if (contentType.startsWith('audio/') || /\.(mp3|wav|flac|aac|m4a)$/.test(name)) return 'audio'
  if (/\.(docx|xlsx|pptx)$/.test(name)) return 'office'
  return 'unknown'
}

async function handlePreview(file: ManagedFileAsset): Promise<void> {
  releasePreviewUrl()
  previewFile.value = file
  previewType.value = getPreviewType(file)
  officePreview.value = null
  previewVisible.value = true
  previewLoading.value = previewType.value !== 'unknown'
  if (previewType.value === 'unknown') return

  try {
    if (previewType.value === 'office') {
      officePreview.value = await getOfficePreview(file.id)
    } else {
      const blob = await downloadFile(file.id)
      previewUrl.value = URL.createObjectURL(blob)
    }
  } catch {
    previewType.value = 'unknown'
    ElMessage.error('预览加载失败')
  } finally {
    previewLoading.value = false
  }
}

function releasePreviewUrl(): void {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
}

function handlePreviewClose(): void {
  releasePreviewUrl()
  previewFile.value = null
  officePreview.value = null
  previewType.value = 'unknown'
  previewLoading.value = false
}

const versionVisible = ref(false)
const versionFile = ref<ManagedFileAsset | null>(null)
const versions = ref<FileVersion[]>([])
const versionLoading = ref(false)
const versionUploading = ref(false)

async function loadVersions(): Promise<void> {
  if (!versionFile.value) return
  versionLoading.value = true
  try {
    versions.value = await getFileVersions(versionFile.value.id)
  } finally {
    versionLoading.value = false
  }
}

function openVersionDialog(file: ManagedFileAsset): void {
  versionFile.value = file
  versionVisible.value = true
  void loadVersions()
}

async function handleVersionUpload(file: UploadFile): Promise<void> {
  if (!versionFile.value || !file.raw || versionUploading.value) return
  versionUploading.value = true
  try {
    const updated = await uploadFileVersion(versionFile.value.id, file.raw)
    versionFile.value = { ...versionFile.value, ...updated }
    ElMessage.success(`已上传 v${updated.version}`)
    await Promise.all([loadVersions(), loadData()])
  } finally {
    versionUploading.value = false
  }
}

async function handleVersionDownload(version: FileVersion): Promise<void> {
  if (!versionFile.value) return
  const blob = await downloadFileVersion(versionFile.value.id, version.id)
  downloadBlob(blob, `${versionFile.value.name}_v${version.version}`)
}

async function handleVersionRestore(version: FileVersion): Promise<void> {
  if (!versionFile.value) return
  await ElMessageBox.confirm(`确定恢复 v${version.version} 吗？`, '恢复历史版本', { type: 'warning' })
  const updated = await restoreFileVersion(versionFile.value.id, version.id)
  versionFile.value = { ...versionFile.value, ...updated }
  ElMessage.success(`已恢复为 v${updated.version}`)
  await Promise.all([loadVersions(), loadData()])
}

onMounted(async () => {
  await Promise.all([loadProjects(), loadTeams()])
  await Promise.all([loadTags(), loadData()])
  const fileId = positiveQueryId(route.query.file_id)
  if (fileId) {
    try {
      await handlePreview(await getFile(fileId))
    } catch {
      // 请求层已经展示无权访问或文件不存在的错误。
    }
  }
})

onUnmounted(releasePreviewUrl)
</script>

<style lang="scss" scoped>
.form-help {
  width: 100%;
  margin: 6px 0 0;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.el-form > :deep(.el-alert) {
  margin-bottom: 16px;
}

.file-list-page {
  padding-bottom: 32px;
}

.page-meta {
  display: inline-block;
  margin-top: 7px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.file-workspace,
.trash-workspace {
  min-width: 0;
  overflow: hidden;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
}

.filter-toolbar {
  padding: 14px 18px;
  border-bottom: 1px solid var(--color-border-light);
}

.filter-toolbar :deep(.el-form) {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.filter-toolbar :deep(.el-form-item) {
  margin-right: 0;
  margin-bottom: 0;
}

.project-filter { width: 200px; }
.folder-filter { width: 210px; }
.tag-filter { width: 150px; }
.level-filter { width: 120px; }
.search-filter { width: 180px; }

.tag-option-dot,
.tag-swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  margin-right: 7px;
  border-radius: 50%;
  vertical-align: 1px;
}

.workspace-body {
  display: grid;
  min-width: 0;
  grid-template-columns: 230px minmax(0, 1fr);
}

.workspace-body.without-sidebar {
  grid-template-columns: minmax(0, 1fr);
}

.folder-sidebar {
  min-height: 560px;
  padding: 12px 10px;
  overflow: hidden;
  border-right: 1px solid var(--color-border-light);
}

.folder-sidebar-heading {
  display: flex;
  height: 34px;
  padding: 0 6px;
  align-items: center;
  justify-content: space-between;
  color: var(--color-text);
  font-size: 13px;
}

.folder-root {
  display: flex;
  width: 100%;
  height: 34px;
  padding: 0 9px;
  align-items: center;
  gap: 8px;
  color: var(--color-text-regular);
  font: inherit;
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.folder-root:hover,
.folder-root.active {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.folder-sidebar :deep(.el-tree-node__content) {
  height: 36px;
  border-radius: var(--radius-sm);
}

.folder-node {
  display: flex;
  min-width: 0;
  width: 100%;
  align-items: center;
  gap: 6px;
}

.folder-node-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.folder-count {
  margin-left: auto;
  color: var(--color-text-muted);
  font-size: 11px;
}

.folder-node-actions {
  display: none;
  margin-left: auto;
  align-items: center;
}

.folder-node:hover .folder-count { display: none; }
.folder-node:hover .folder-node-actions { display: flex; }
.folder-node-actions :deep(.el-button) { width: 24px; height: 24px; padding: 0; }

.file-results { min-width: 0; }

.directory-context {
  display: grid;
  gap: 12px;
  padding: 14px 18px;
  background: var(--color-surface-subtle);
  border-bottom: 1px solid var(--color-border-light);
}

.breadcrumb-button {
  padding: 0;
  color: var(--color-text-muted);
  font: inherit;
  background: transparent;
  border: 0;
  cursor: pointer;
}

.breadcrumb-button:hover,
.breadcrumb-button.current {
  color: var(--color-primary);
}

.directory-current-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.directory-current-copy {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.directory-current-copy > span {
  color: var(--color-text-muted);
  font-size: 11px;
}

.directory-current-copy > strong {
  overflow: hidden;
  color: var(--color-text);
  font-size: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.directory-current-copy > p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.directory-actions {
  display: flex;
  flex: 0 0 auto;
  gap: 8px;
}

.directory-actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.child-folder-section {
  padding: 12px 18px 14px;
  border-bottom: 1px solid var(--color-border-light);
}

.child-folder-heading {
  display: flex;
  margin-bottom: 9px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--color-text);
  font-size: 12px;
}

.child-folder-heading > span {
  color: var(--color-text-muted);
  font-size: 11px;
}

.child-folder-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 8px;
}

.child-folder-card {
  display: flex;
  min-width: 0;
  padding: 10px 11px;
  align-items: center;
  gap: 9px;
  color: var(--color-text-regular);
  font: inherit;
  text-align: left;
  background: var(--color-surface);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.child-folder-card:hover {
  color: var(--color-primary);
  border-color: var(--color-primary);
}

.child-folder-card > .el-icon {
  flex: 0 0 auto;
  color: var(--color-primary);
  font-size: 20px;
}

.child-folder-card > span {
  display: grid;
  min-width: 0;
  flex: 1;
  gap: 2px;
}

.child-folder-card strong,
.child-folder-card small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.child-folder-card strong {
  font-size: 13px;
  font-weight: 600;
}

.child-folder-card small {
  color: var(--color-text-muted);
  font-size: 10px;
}

.child-folder-card em {
  flex: 0 0 auto;
  color: var(--color-primary);
  font-size: 11px;
  font-style: normal;
}

.list-heading {
  display: flex;
  min-height: 54px;
  padding: 12px 18px;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--color-border-light);
}

.list-heading > div {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.list-heading h2 {
  margin: 0;
  color: var(--color-text);
  font-size: 16px;
  font-weight: 600;
}

.list-heading > span {
  flex: 0 0 auto;
  color: var(--color-text-muted);
  font-size: 12px;
}

.sensitive-count {
  color: var(--color-danger);
  font-size: 11px;
  font-weight: 600;
}

.file-table-shell {
  min-width: 0;
  overflow-x: auto;
}

.file-table-shell :deep(.el-table) { min-width: 1040px; }
.file-table-shell :deep(.sensitive-file-row > td.el-table__cell) { background: var(--danger-light); }

.file-cell,
.mobile-file-title {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
}

.file-icon-box {
  display: inline-flex;
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
  background: var(--color-primary-soft);
  border: 1px solid rgba(23, 107, 115, 0.18);
  border-radius: var(--radius-sm);
}

.file-icon-box.is-sensitive {
  color: var(--color-danger);
  background: var(--danger-light);
  border-color: rgba(182, 66, 66, 0.22);
}

.file-cell > div,
.mobile-file-title > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.file-cell strong,
.mobile-file-title h3 {
  overflow: hidden;
  color: var(--color-text);
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-cell > div > span,
.mobile-file-title > div > span,
.muted-value {
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-tags {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.file-tags :deep(.el-tag) { max-width: 88px; overflow: hidden; text-overflow: ellipsis; }
.tag-more { color: var(--color-text-muted); font-size: 11px; }

.mobile-file-list {
  display: flex;
  padding: 12px;
  flex-direction: column;
  gap: 10px;
}

.mobile-file-card {
  padding: 14px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.mobile-file-card.is-sensitive { border-color: rgba(182, 66, 66, 0.34); }
.mobile-file-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.mobile-file-title { flex: 1; }
.mobile-file-title h3 { max-width: 100%; margin: 0; font-size: 14px; }
.mobile-tags { margin-top: 12px; }

.mobile-file-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 16px;
  margin: 14px 0 0;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.mobile-file-meta .meta-wide { grid-column: 1 / -1; }
.mobile-file-meta dt { margin-bottom: 3px; color: var(--color-text-muted); font-size: 11px; }
.mobile-file-meta dd { margin: 0; overflow: hidden; color: var(--color-text-regular); font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }

.mobile-file-actions {
  display: flex;
  margin-top: 12px;
  padding-top: 9px;
  justify-content: flex-end;
  gap: 4px;
  border-top: 1px solid var(--color-border-light);
}

.mobile-file-actions :deep(.el-button + .el-button) { margin-left: 0; }

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  padding: 12px 18px 16px;
  border-top: 1px solid var(--color-border-light);
}

.upload-icon { font-size: 28px; color: var(--color-primary); }
.upload-label { margin-top: 7px; color: var(--color-text-regular); }

.scope-target-select {
  width: 100%;
  margin-top: 10px;
}

.tag-editor {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 44px auto auto;
  gap: 10px;
  align-items: center;
}

.tag-list,
.share-list {
  display: flex;
  max-height: 390px;
  margin-top: 18px;
  overflow-y: auto;
  flex-direction: column;
  border-top: 1px solid var(--color-border-light);
}

.tag-row,
.share-row {
  display: flex;
  min-height: 52px;
  padding: 9px 4px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--color-border-light);
}

.tag-row > div { display: flex; align-items: center; min-width: 0; }
.tag-row strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.tag-checkbox-list { min-height: 120px; }
.tag-checkbox-list :deep(.el-checkbox-group) { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
.tag-checkbox-list :deep(.el-checkbox) { min-width: 0; margin-right: 0; }
.tag-checkbox-list :deep(.el-checkbox__label) { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.share-create-row {
  display: grid;
  grid-template-columns: minmax(190px, 1fr) 150px auto;
  gap: 10px;
}

.share-main { display: flex; min-width: 0; flex-direction: column; gap: 4px; }
.share-main > div { display: flex; align-items: center; gap: 8px; }
.share-main code { overflow: hidden; color: var(--color-text); text-overflow: ellipsis; }
.share-main > span { color: var(--color-text-muted); font-size: 12px; }
.share-actions { display: flex; align-items: center; }

.sensitive-preview-alert {
  display: flex;
  margin-bottom: 12px;
  padding: 10px 12px;
  align-items: center;
  gap: 8px;
  color: var(--color-danger);
  font-size: 12px;
  font-weight: 600;
  background: var(--danger-light);
  border: 1px solid rgba(182, 66, 66, 0.24);
  border-radius: var(--radius-sm);
}

.preview-container,
.preview-loading {
  display: flex;
  min-height: 420px;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.preview-image { max-width: 100%; max-height: 68vh; object-fit: contain; }
.preview-iframe { width: 100%; height: 68vh; border: none; }
.preview-video { max-width: 100%; max-height: 68vh; }
.preview-audio { width: min(640px, calc(100% - 32px)); }

.office-preview {
  max-height: 68vh;
  padding: 18px;
  overflow: auto;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
}

.office-section {
  padding: 4px 0 20px;
  border-bottom: 1px solid var(--color-border-light);
}

.office-section:last-child { border-bottom: 0; }
.office-section h3 { margin: 10px 0; color: var(--color-text); font-size: 15px; }
.office-section p { margin: 6px 0; color: var(--color-text-regular); line-height: 1.65; white-space: pre-wrap; overflow-wrap: anywhere; }
.office-table-shell { max-width: 100%; margin-top: 12px; overflow: auto; }
.office-table-shell table { min-width: 100%; border-collapse: collapse; font-size: 12px; }
.office-table-shell td { min-width: 92px; max-width: 320px; padding: 7px 9px; color: var(--color-text-regular); overflow-wrap: anywhere; border: 1px solid var(--color-border); }

.version-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 0 18px;
  color: var(--color-text);
  font-size: 14px;
}

@media screen and (max-width: 768px) {
  .file-list-page { padding-bottom: calc(88px + env(safe-area-inset-bottom)); }
  .filter-toolbar { padding: 14px; }
  .filter-toolbar :deep(.el-form) { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px 10px; }
  .filter-toolbar :deep(.el-form-item) { display: block; min-width: 0; }
  .filter-toolbar :deep(.el-form-item:last-child) { grid-column: 1 / -1; }
  .filter-toolbar :deep(.el-form-item__label) { display: block; width: 100%; height: auto; margin-bottom: 5px; line-height: 1.4; }
  .project-filter, .folder-filter, .tag-filter, .level-filter, .search-filter { width: 100%; }
  .workspace-body { display: block; }
  .directory-context { padding: 12px 14px; }
  .directory-current-row { align-items: stretch; flex-direction: column; gap: 10px; }
  .directory-actions { display: grid; grid-template-columns: 1fr 1fr; }
  .directory-actions :deep(.el-button) { width: 100%; }
  .child-folder-section { padding: 11px 14px 13px; }
  .child-folder-heading { align-items: flex-start; flex-direction: column; gap: 2px; }
  .child-folder-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .list-heading { padding-right: 14px; padding-left: 14px; }
  .pagination-wrapper { justify-content: center; padding-right: 8px; padding-left: 8px; }
  .preview-container, .preview-loading { min-height: 300px; }
  .preview-iframe, .office-preview { height: 62vh; max-height: 62vh; }
  .tag-editor { grid-template-columns: minmax(0, 1fr) 44px auto; }
  .tag-editor > :last-child { grid-column: 1 / -1; }
  .share-create-row { grid-template-columns: 1fr; }
  .tag-checkbox-list :deep(.el-checkbox-group) { grid-template-columns: 1fr; }
  .version-toolbar { align-items: stretch; flex-direction: column; }
}

@media screen and (max-width: 430px) {
  .filter-toolbar :deep(.el-form) { grid-template-columns: 1fr; }
  .filter-toolbar :deep(.el-form-item:last-child) { grid-column: auto; }
  .directory-actions,
  .child-folder-grid { grid-template-columns: 1fr; }
  .tag-editor { grid-template-columns: minmax(0, 1fr) 44px; }
  .tag-editor > .el-button { grid-column: 1 / -1; }
  .share-row { align-items: flex-start; flex-direction: column; }
  .share-actions { align-self: flex-end; }
}
</style>
