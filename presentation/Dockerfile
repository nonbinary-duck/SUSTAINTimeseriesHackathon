# Use the full texlive distribution
FROM texlive/texlive:latest-full

# Set the working directory inside the container
WORKDIR /workdir

# The actual compilation command will be handled by docker-compose 
# or passed as a CMD here.
CMD ["lualatex", "main.tex"]