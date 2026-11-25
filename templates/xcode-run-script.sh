# 加到 Xcode 的 Build Phases → Run Script（放在 Compile Sources 之后）
# 作用：构建后立刻检查「新增文件有没有注册到 pbxproj」这类问题
DC="$HOME/ops/dc"
if [ -x "$DC" ]; then
  "$DC" ios check --fast --repo "$SRCROOT" || {
    echo "error: doublecheck 检查未通过（见上方输出）"
    exit 1
  }
fi
